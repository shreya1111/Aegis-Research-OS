/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Standalone output keeps the production image minimal (design §11.4).
  output: 'standalone',
  eslint: {
    dirs: ['app', 'components', 'lib', 'types', 'tests'],
  },
  experimental: {
    typedRoutes: false,
  },
};

export default nextConfig;
