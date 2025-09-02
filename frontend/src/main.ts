import themes from 'devextreme/ui/themes';
import { platformBrowser } from '@angular/platform-browser';
import { AppModule } from './app/app.module';
import Userback from '@userback/widget';

themes.initialized(() => {
  platformBrowser().bootstrapModule(AppModule, {
  ngZoneEventCoalescing: true,
})
    .then((moduleRef) => {
      // Initialize Userback after app is bootstrapped
      initializeUserback(moduleRef);
    })
    .catch(err => console.error(err));
});

function initializeUserback(moduleRef: any) {
  // Get current user data from localStorage if available
  const currentUserData = localStorage.getItem('current_user');
  let userbackOptions = {};

  if (currentUserData) {
    try {
      const user = JSON.parse(currentUserData);
      userbackOptions = {
        user_data: {
          id: user.id,
          info: {
            name: user.email.split('@')[0], // Use email prefix as name if no name field
            email: user.email,
            role: user.role_band || 'User',
            title: user.role_title || 'Employee'
          }
        }
      };
    } catch (error) {
      console.warn('Failed to parse user data for Userback:', error);
    }
  }

  // Initialize Userback with the token and user options
  Userback("A-9lhEHbFuA9WbEToHhO1bcWmJC", userbackOptions)
    .then(() => {
      console.log("Userback successfully initialized");
      
      // Get the UserbackService and mark it as initialized
      try {
        const injector = moduleRef.injector;
        const userbackService = injector.get('UserbackService');
        if (userbackService) {
          userbackService.initialize();
        }
      } catch (error) {
        console.warn('Could not initialize UserbackService:', error);
      }
    })
    .catch((error) => {
      console.error("Failed to initialize Userback:", error);
    });
}
