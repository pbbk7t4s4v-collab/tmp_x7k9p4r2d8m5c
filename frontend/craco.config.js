import path from 'path';
import { fileURLToPath } from 'url';

// These two lines replace __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const webpack = {
    alias: {
        '@': path.resolve(__dirname, 'src')
    }
};