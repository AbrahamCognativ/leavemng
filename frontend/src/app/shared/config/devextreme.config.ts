import config from 'devextreme/core/config';
import { licenseKey } from '../../../devextreme-license';

export function configureDevExtreme() {
    // Replace 'YOUR_LICENSE_KEY' with your actual DevExtreme license key
    config({
        licenseKey: licenseKey
    });
} 