import themes from 'devextreme/ui/themes';
import { platformBrowser } from '@angular/platform-browser';
import { AppModule } from './app/app.module';

themes.initialized(() => {
  platformBrowser().bootstrapModule(AppModule, {
  ngZoneEventCoalescing: true,
})
    .catch(err => console.error(err));
});
