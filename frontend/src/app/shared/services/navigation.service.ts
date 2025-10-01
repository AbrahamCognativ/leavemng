import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { PolicyAcknowledmentService, UserPolicyStatus } from './policy-acknowledgment.service';
import { AuthService } from './auth.service';

export interface NavigationItem {
  text: string;
  path?: string;
  icon?: string;
  items?: NavigationItem[];
  badge?: {
    text: string;
    type: 'success' | 'warning' | 'error' | 'info';
  };
}

@Injectable({
  providedIn: 'root'
})
export class NavigationService {
  private navigationItemsSubject = new BehaviorSubject<NavigationItem[]>([]);
  public navigationItems$ = this.navigationItemsSubject.asObservable();

  constructor(
    private policyAcknowledmentService: PolicyAcknowledmentService,
    private authService: AuthService
  ) {}

  async updateNavigation(): Promise<void> {
    try {
      const baseNavigation = this.getBaseNavigation();
      
      // Update policies navigation with dynamic policy links
      const policiesNavIndex = baseNavigation.findIndex(item => item.text === 'Policies');
      if (policiesNavIndex !== -1) {
        const userPolicies = await this.policyAcknowledmentService.getUserPolicyStatus();
        baseNavigation[policiesNavIndex] = this.buildPoliciesNavigation(userPolicies);
      }

      this.navigationItemsSubject.next(baseNavigation);
    } catch (error) {
      console.error('Error updating navigation:', error);
      // Fallback to base navigation
      this.navigationItemsSubject.next(this.getBaseNavigation());
    }
  }

  private getBaseNavigation(): NavigationItem[] {
    const isAdmin = this.authService.isAdmin;
    const isHR = this.authService.isHR;
    const isManager = this.authService.isManager;

    return [
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
          ...(isAdmin || isHR || isManager ? [
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
          ...(isAdmin || isHR || isManager ? [
            {
              text: 'Requests',
              path: '/admin/wfh-requests',
            }
          ] : [])
        ]
      },
      {
        text: 'Policies',
        icon: 'doc',
        items: [] // This will be populated dynamically
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
          ...(isAdmin || isHR ? [
            {
              text: 'Policies',
              path: '/admin/policies',
            },
            {
              text: 'Policy Stats',
              path: '/admin/policy-acknowledgments',
            }
          ] : []),
          ...(isAdmin || isHR || isManager ? [
            {
              text: 'User Docs',
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
  }

  private buildPoliciesNavigation(userPolicies: UserPolicyStatus[]): NavigationItem {
    const pendingCount = userPolicies.filter(p => !p.is_acknowledged).length;
    const overdueCount = userPolicies.filter(p => p.is_overdue).length;

    const policiesNav: NavigationItem = {
      text: 'Policies',
      icon: 'doc',
      items: []
    };

    // Add all policies (both acknowledged and pending) as individual dropdown items
    if (userPolicies.length > 0) {
      userPolicies.forEach(policy => {
        const isOverdue = policy.is_overdue;
        const isUrgent = !policy.is_acknowledged && !isOverdue && policy.days_remaining !== null && policy.days_remaining !== undefined && policy.days_remaining <= 2;
        const isPending = !policy.is_acknowledged;

        let badge: { text: string; type: 'success' | 'warning' | 'error' | 'info' } | undefined = undefined;
        if (isPending) {
          badge = {
            text: isOverdue ? 'OVERDUE' : isUrgent ? 'URGENT' : 'NEW',
            type: isOverdue ? 'error' : isUrgent ? 'warning' : 'info'
          };
        }

        policiesNav.items!.push({
          text: policy.policy_name,
          path: `/policy/${policy.policy_id}`,
          badge: badge
        });
      });
    } else {
      // If no policies, show a placeholder
      policiesNav.items!.push({
        text: 'No policies',
        path: undefined
      });
    }

    return policiesNav;
  }

  getNavigationItems(): NavigationItem[] {
    return this.navigationItemsSubject.value;
  }

  async refreshNavigation(): Promise<void> {
    await this.updateNavigation();
  }

  // Helper method to get pending policies count for badges
  async getPendingPoliciesCount(): Promise<number> {
    try {
      const userPolicies = await this.policyAcknowledmentService.getUserPolicyStatus();
      return userPolicies.filter(p => !p.is_acknowledged).length;
    } catch (error) {
      return 0;
    }
  }

  // Helper method to get overdue policies count
  async getOverduePoliciesCount(): Promise<number> {
    try {
      const userPolicies = await this.policyAcknowledmentService.getUserPolicyStatus();
      return userPolicies.filter(p => p.is_overdue).length;
    } catch (error) {
      return 0;
    }
  }
}