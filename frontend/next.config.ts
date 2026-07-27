import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
      {
        source: '/health',
        destination: 'http://127.0.0.1:8000/health',
      },
      {
        source: '/metrics',
        destination: 'http://127.0.0.1:8000/metrics',
      },
    ];
  },
  env: {
    NEXT_PUBLIC_API_URL: '/api',
  },
};

export default nextConfig;
