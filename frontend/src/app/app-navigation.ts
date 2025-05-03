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
    path: '/admin',
    icon: 'preferences'
  },
  {
    text: 'Profile',
    path: '/profile',
    icon: 'user'
  }
];

