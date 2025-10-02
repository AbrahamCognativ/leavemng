import { AuthService } from './shared/services';

// This is now a fallback - the NavigationService will provide dynamic navigation
export const getNavigationItems = (authService: AuthService) => [
  {
    text: 'Dashboard',
    path: '/dashboard',
    icon: 'home'
  },
  {
    text: 'Leave Management',
    icon: 'description',
    items: [
      {
        text: 'Apply',
        path: '/leave/apply',
      },
      {
        text: 'Leave History',
        path: '/leave/history',
      },
      {
        text: 'Schedule',
        path: '/leave/schedule',
      },
      ...(authService.isAdmin || authService.isHR || authService.isManager ? [
        {
          text: 'Requests',
          path: '/admin/leaves',
        }
      ] : [])
    ]
  },
  {
    text: 'Work From Home',
    icon: 'home',
    items: [
      {
        text: 'Dashboard',
        path: '/wfh/dashboard',
      },
      {
        text: 'Apply',
        path: '/wfh/apply',
      },
      ...(authService.isAdmin || authService.isHR || authService.isManager ? [
        {
          text: 'Requests',
          path: '/admin/wfh-requests',
        }
      ] : [])
    ]
  },
  {
    text: 'Policies',
    path: '/policies',
    icon: 'doc'
  },
  {
    text: 'Docs',
    path: '/docs',
    icon: 'folder'
  },
  {
    text: 'Admin',
    icon: 'preferences',
    items: [
      {
        text: 'Dashboard',
        path: '/admin/leave-requests',
      },
      {
        text: 'Leave Types',
        path: '/admin/leave-types',
      },
      {
        text: 'Org Units',
        path: '/admin/org-units',
      },
      {
        text: 'Users',
        path: '/admin/employee-invite',
      },
      ...(authService.isAdmin || authService.isHR ? [
        {
          text: 'Manage Policies',
          path: '/admin/policies',
        }
      ] : []),
      ...(authService.isAdmin || authService.isHR || authService.isManager ? [
        {
          text: 'User Documents',
          path: '/admin/user-documents',
        }
      ] : []),
      {
        text: 'Audit Logs',
        path: '/admin/audit-logs',
      }
    ]
  }
];

