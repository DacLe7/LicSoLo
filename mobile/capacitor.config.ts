import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "vn.lacvietnode.lich",
  appName: "Trợ lý thời gian",
  webDir: "dist",
  plugins: {
    CapacitorHttp: { enabled: true },
    BackgroundRunner: {
      // phải khớp RUNNER_LABEL / RUNNER_EVENT trong src/config.ts (có test kiểm tra); cap không nạp được import tương đối
      label: "vn.lacvietnode.lich.bg",
      src: "runners/runner.js",
      event: "syncReminders",
      repeat: true,
      interval: 15,
      autoStart: true,
    },
  },
};

export default config;
