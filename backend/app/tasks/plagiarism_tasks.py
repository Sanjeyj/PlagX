import asyncio
import json
import logging
from pathlib import Path
from asgiref.sync import async_to_sync

from celery import shared_task
from app.config import get_settings
from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.report import Report
from app.engine.distributed_pipeline import DistributedPipeline

settings = get_settings()
logger = logging.getLogger(__name__)

def update_doc_status(doc_id: str, status: str, progress: int, stage: str, job_id: str = None):
    """Safely update document status in async db from sync celery worker."""
    async def _update():
        async for db in get_db():
            doc = await db.get(Document, doc_id)
            if doc:
                doc.status = status
                doc.progress = progress
                doc.worker_stage = stage
                if job_id:
                    doc.job_id = job_id
                await db.commit()
    async_to_sync(_update)()

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, soft_time_limit=300, time_limit=360)
def extract_document_task(self, doc_id: str):
    logger.info(f"Worker starting extraction for {doc_id}")
    update_doc_status(doc_id, DocumentStatus.EXTRACTING.value, 10, "Extracting text", self.request.id)
    
    # We use a Pipeline instance but only run the extraction part
    async def _extract():
        async for db in get_db():
            pipeline = DistributedPipeline(db)
            return await pipeline.run_stage_extraction(doc_id, f"{settings.upload_path}/{doc_id}")
            
    extracted_data = async_to_sync(_extract)()
    
    # Checkpoint
    cache_dir = Path(settings.upload_path) / "worker_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_dir / f"{doc_id}_extraction.json", "w", encoding="utf-8") as f:
        json.dump(extracted_data, f)
        
    return doc_id


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, soft_time_limit=600, time_limit=700)
def embedding_generation_task(self, doc_id: str):
    logger.info(f"Worker starting embeddings for {doc_id}")
    update_doc_status(doc_id, DocumentStatus.EMBEDDING.value, 30, "Generating embeddings", self.request.id)
    
    cache_dir = Path(settings.upload_path) / "worker_cache"
    with open(cache_dir / f"{doc_id}_extraction.json", "r", encoding="utf-8") as f:
        extracted_data = json.load(f)

    async def _embed():
        async for db in get_db():
            pipeline = DistributedPipeline(db)
            return await pipeline.run_stage_embeddings(doc_id, extracted_data)
            
    embedding_data = async_to_sync(_embed)()
    
    with open(cache_dir / f"{doc_id}_embeddings.json", "w", encoding="utf-8") as f:
        json.dump(embedding_data, f)
        
    return doc_id


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, soft_time_limit=600, time_limit=700)
def semantic_analysis_task(self, doc_id: str):
    logger.info(f"Worker starting semantic analysis for {doc_id}")
    update_doc_status(doc_id, DocumentStatus.ANALYZING.value, 50, "FAISS semantic retrieval", self.request.id)
    
    cache_dir = Path(settings.upload_path) / "worker_cache"
    with open(cache_dir / f"{doc_id}_embeddings.json", "r", encoding="utf-8") as f:
        embedding_data = json.load(f)
    with open(cache_dir / f"{doc_id}_extraction.json", "r", encoding="utf-8") as f:
        extracted_data = json.load(f)

    async def _analyze():
        async for db in get_db():
            pipeline = DistributedPipeline(db)
            return await pipeline.run_stage_semantic(doc_id, extracted_data, embedding_data)
            
    semantic_data = async_to_sync(_analyze)()
    
    with open(cache_dir / f"{doc_id}_semantic.json", "w", encoding="utf-8") as f:
        json.dump(semantic_data, f)
        
    return doc_id


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, soft_time_limit=300, time_limit=360)
def citation_and_scoring_task(self, doc_id: str):
    logger.info(f"Worker starting scoring for {doc_id}")
    update_doc_status(doc_id, DocumentStatus.SCORING.value, 75, "Citation analysis and scoring", self.request.id)
    
    cache_dir = Path(settings.upload_path) / "worker_cache"
    with open(cache_dir / f"{doc_id}_semantic.json", "r", encoding="utf-8") as f:
        semantic_data = json.load(f)
    with open(cache_dir / f"{doc_id}_extraction.json", "r", encoding="utf-8") as f:
        extracted_data = json.load(f)

    async def _score():
        async for db in get_db():
            pipeline = DistributedPipeline(db)
            return await pipeline.run_stage_scoring(doc_id, extracted_data, semantic_data)
            
    report_id = async_to_sync(_score)()
    return doc_id, report_id


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, soft_time_limit=300, time_limit=360)
def pdf_generation_task(self, args: tuple):
    doc_id, report_id = args
    logger.info(f"Worker starting PDF generation for {doc_id} -> Report {report_id}")
    update_doc_status(doc_id, DocumentStatus.GENERATING_PDF.value, 90, "Generating PDF", self.request.id)
    
    async def _pdf():
        async for db in get_db():
            from app.services.report_service import ReportService
            report_svc = ReportService()
            # Fetch report
            report = await db.get(Report, report_id)
            if report:
                await report_svc.generate_pdf_for_report(report)
                
            # Mark complete
            doc = await db.get(Document, doc_id)
            if doc:
                doc.status = DocumentStatus.COMPLETED.value
                doc.progress = 100
                doc.worker_stage = "Finished"
                await db.commit()
                
    async_to_sync(_pdf)()
    return doc_id


@shared_task(bind=True)
def document_pipeline_error_handler(self, request, exc, traceback, doc_id: str):
    """Fallback handler if the chain completely fails."""
    logger.error(f"Pipeline failed for {doc_id}: {exc}")
    update_doc_status(doc_id, DocumentStatus.FAILED.value, 0, f"Error: {str(exc)}")
