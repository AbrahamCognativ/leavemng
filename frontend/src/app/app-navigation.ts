import { AuthService } from './shared/services';

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
      {
        text: 'Audit Logs',
        path: '/admin/audit-logs',
      }
    ]
  },
  {
    text: 'Profile',
    path: '/profile',
    icon: 'user'
  }
];

