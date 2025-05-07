export const navigation = [
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
      }
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
      }
    ]
  },
  {
    text: 'Profile',
    path: '/profile',
    icon: 'user'
  }
];

