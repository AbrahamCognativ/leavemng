# Leave Management System - Frontend

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 19.2.10 and uses [DevExtreme](https://js.devexpress.com/) for UI components.

## Prerequisites

- Node.js (v18 or later)
- npm (v9 or later)
- Angular CLI (v19.2.10)
- DevExtreme License Key

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure DevExtreme License:
   - Create a file `src/devextreme-license.ts` in the frontend directory
   - Add your DevExtreme license key:
   ```typescript
   export const licenseKey = 'YOUR_LICENSE_KEY';
   ```
   - Replace 'YOUR_LICENSE_KEY' with your actual DevExtreme license key
   - The license key can be obtained from your DevExtreme account dashboard or purchase confirmation email

3. Build themes:
```bash
npm run build-themes
```

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## DevExtreme Components

This project uses several DevExtreme components:
- DataGrid for data display and management
- Form for data input
- DateBox and Calendar for date selection
- Charts for data visualization
- SelectBox for dropdown selections
- Button for actions
- LoadIndicator for loading states

## Additional Resources

- [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli)
- [DevExtreme Documentation](https://js.devexpress.com/Documentation/)
- [DevExtreme Angular Components](https://js.devexpress.com/Documentation/Guide/Angular_Components/DevExtreme_Angular_Components/)
