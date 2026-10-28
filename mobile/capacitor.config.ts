import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "vn.lacvietnode.lich",
  appName: "Trợ lý thời gian",
  webDir: "dist",
  plugins: {
    CapacitorHttp: { enabled: true },
  },
};

export default config;
