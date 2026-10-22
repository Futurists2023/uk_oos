/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  headers: async () => [
    {
      source: '/:path*',
      headers: [
        {
          key: 'X-Robots-Tag',
          value: 'noindex, nofollow, noarchive'
        }
      ]
    }
  ]
};

export default nextConfig;
