/** @type {import('next').NextConfig} */
const nextConfig = {
    rewrites: async () => {
        return [
          {
            source: '/api/generate',
            destination: 'http://localhost:8000/generate',
          },
        ]
      },
};

export default nextConfig;
