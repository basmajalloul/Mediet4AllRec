import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.mediet4all.mobile',
  appName: 'meddiet4all',
  webDir: 'build',
  server: {
    url: "https://mediet4allrec.streamlit.app/"
  }
};

export default config;
