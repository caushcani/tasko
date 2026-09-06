/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // The dev server runs in a container on :3000, reached via the compose
  // port mapping at localhost:3100 — a different origin, which Next 15.2+
  // blocks for /_next/* dev resources by default. Without this the page
  // renders (SSR) but never hydrates, so nothing interactive works.
  allowedDevOrigins: ['localhost', '127.0.0.1'],
}

export default nextConfig
