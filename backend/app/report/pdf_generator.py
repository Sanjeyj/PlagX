"""
PDF Report Generator using Playwright
Uses headless Chromium for browser-accurate PDF rendering.
"""

import logging
import asyncio
import time
import traceback
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generates PDF reports from HTML using Playwright headless Chromium."""

    async def generate(self, html_content: str, output_path: str, report_id: str = None) -> str:
        """Convert HTML report to PDF using Playwright."""
        from playwright.async_api import async_playwright

        start_time = time.time()
        logger.info(f"Starting PDF generation for report_id={report_id} to output_path={output_path}")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with async_playwright() as p:
                logger.debug(f"Launching Playwright Chromium for report_id={report_id}")
                browser = await p.chromium.launch(headless=True)
                logger.debug(f"Playwright Chromium launched successfully for report_id={report_id}")
                page = await browser.new_page()

                logger.debug(f"Setting HTML content on page for report_id={report_id}")
                await page.set_content(html_content, wait_until="networkidle")
                await page.wait_for_timeout(1000)  # Allow fonts/styles to load

                logger.debug(f"Writing PDF to path={output} for report_id={report_id}")
                await page.pdf(
                    path=str(output),
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "20mm",
                        "bottom": "20mm",
                        "left": "15mm",
                        "right": "15mm",
                    },
                    display_header_footer=True,
                    header_template='<div style="font-size:8px;color:#94a3b8;width:100%;text-align:center;font-family:Inter,sans-serif;">PlagX AI Plagiarism Report</div>',
                    footer_template='<div style="font-size:8px;color:#94a3b8;width:100%;text-align:center;font-family:Inter,sans-serif;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
                )

                await browser.close()

            duration = time.time() - start_time
            if output.exists():
                file_size = output.stat().st_size
                logger.info(
                    f"PDF generation SUCCESS for report_id={report_id}. "
                    f"Path: {output}, Size: {file_size} bytes, Duration: {duration:.2f}s"
                )
            else:
                logger.error(
                    f"PDF generation FAILED for report_id={report_id}. "
                    f"File does not exist at {output} after execution. Duration: {duration:.2f}s"
                )
                raise FileNotFoundError(f"PDF file was not created at {output}")

            return str(output)
        except Exception as e:
            duration = time.time() - start_time
            tb = traceback.format_exc()
            logger.error(
                f"PDF generation EXCEPTION for report_id={report_id}. "
                f"Duration: {duration:.2f}s. Error: {e}\nTraceback:\n{tb}"
            )
            raise e

    def generate_in_thread(self, html_content: str, output_path: str, report_id: str = None) -> str:
        """Synchronously execute the async PDF generation in a dedicated background thread with its own event loop."""
        import threading
        import queue
        import sys

        result_queue = queue.Queue()

        def worker():
            if sys.platform == "win32":
                loop = asyncio.ProactorEventLoop()
            else:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.generate(html_content, output_path, report_id)
                )
                result_queue.put((result, None))
            except Exception as e:
                result_queue.put((None, e))
            finally:
                loop.close()

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        result, exception = result_queue.get()
        if exception:
            raise exception
        return result

    @classmethod
    async def validate_browser(cls) -> bool:
        """Validates that Playwright/Chromium is installed and functioning correctly."""
        from playwright.async_api import async_playwright
        import tempfile
        import shutil

        logger.info("Validating Playwright/Chromium installation...")
        temp_dir = tempfile.mkdtemp()
        temp_html = Path(temp_dir) / "test.html"
        temp_pdf = Path(temp_dir) / "test.pdf"

        try:
            temp_html.write_text("<html><body><h1>Test</h1></body></html>", encoding="utf-8")

            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(headless=True)
                except Exception as launch_err:
                    logger.error(f"Playwright chromium launch failed: {launch_err}", exc_info=True)
                    return False

                try:
                    page = await browser.new_page()
                    await page.set_content(temp_html.read_text(encoding="utf-8"), wait_until="networkidle")
                    await page.pdf(path=str(temp_pdf))
                    await browser.close()
                except Exception as render_err:
                    logger.error(f"Playwright page render/PDF write failed: {render_err}", exc_info=True)
                    await browser.close()
                    return False

            if temp_pdf.exists() and temp_pdf.stat().st_size > 0:
                logger.info("Playwright/Chromium validation SUCCESS")
                return True
            else:
                logger.error("Playwright validation failed: PDF file was not created or is empty")
                return False
        except Exception as e:
            logger.error(f"Playwright/Chromium validation unexpected error: {e}", exc_info=True)
            return False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def validate_browser_in_thread(cls) -> bool:
        """Validates that Playwright/Chromium is installed and functioning correctly in a dedicated thread."""
        import threading
        import queue
        import sys

        result_queue = queue.Queue()

        def worker():
            if sys.platform == "win32":
                loop = asyncio.ProactorEventLoop()
            else:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(cls.validate_browser())
                result_queue.put((result, None))
            except Exception as e:
                result_queue.put((False, e))
            finally:
                loop.close()

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        result, exception = result_queue.get()
        if exception:
            logger.error(f"Browser validation thread failed: {exception}", exc_info=True)
            return False
        return result
