/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  eslint: {
    dirs: ["app", "tests"],
  },
};

export default nextConfig;