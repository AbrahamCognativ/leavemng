import { Component, OnInit, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxToastModule } from 'devextreme-angular/ui/toast';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxSelectBoxModule } from 'devextreme-angular/ui/select-box';
import { DxNumberBoxModule } from 'devextreme-angular/ui/number-box';
import { DxiItemModule, DxoLabelModule, DxiColumnModule, DxoPagingModule, DxoPagerModule } from 'devextreme-angular/ui/nested';
import { RouterModule } from '@angular/router';
import { PolicyService, Policy } from '../../../shared/services/policy.service';
import { PolicyAcknowledmentService, PolicyAcknowledmentStats, PolicyNotificationRequest } from '../../../shared/services/policy-acknowledgment.service';
import { AuthService } from '../../../shared/services/auth.service';

@Component({
  selector: 'app-policy-acknowledgments',
  templateUrl: './policy-acknowledgments.component.html',
  styleUrls: ['./policy-acknowledgments.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxDataGridModule,
    DxButtonModule,
    DxToastModule,
    DxPopupModule,
    DxFormModule,
    DxSelectBoxModule,
    DxNumberBoxModule,
    DxiItemModule,
    DxoLabelModule,
    DxiColumnModule,
    DxoPagingModule,
    DxoPagerModule,
    RouterModule
  ]
})
export class PolicyAcknowledmentsComponent implements OnInit, AfterViewInit {
  policyStats: PolicyAcknowledmentStats[] = [];
  policies: Policy[] = [];
  users: any[] = [];
  loading = false;
  toastVisible = false;
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' | 'warning' = 'info';
  
  // Notification popup
  notificationPopupVisible = false;
  selectedPolicy: Policy | null = null;
  notificationFormData = {
    policy_id: '',
    deadline_days: 5
  };
  
  // Details popup
  detailsPopupVisible = false;
  selectedPolicyStats: PolicyAcknowledmentStats | null = null;
  acknowledgmentDetails: any[] = [];

  constructor(
    private policyService: PolicyService,
    private policyAcknowledmentService: PolicyAcknowledmentService,
    private authService: AuthService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.loadData();
  }

  async ngAfterViewInit(): Promise<void> {
    // Ensure data is loaded after view initialization
    if (this.policyStats.length === 0 && !this.loading) {
      setTimeout(() => this.loadData(), 100);
    }
  }

  async loadData(): Promise<void> {
    this.loading = true;
    try {
      // Load policies first, then stats
      await this.loadPolicies();
      await this.loadUsers();
      await this.loadPolicyStats();
    } catch (error) {
      console.error('Error loading data:', error);
      this.showToast('Error loading data', 'error');
    } finally {
      this.loading = false;
    }
  }

  async loadPolicies(): Promise<void> {
    try {
      this.policies = await this.policyService.getPolicies();
    } catch (error) {
      console.error('Error loading policies:', error);
      this.policies = [];
    }
  }

  async loadUsers(): Promise<void> {
    try {
      // Assuming there's a method to get all users
      // You may need to implement this in your user service
      this.users = []; // Placeholder - implement user loading
    } catch (error) {
      console.error('Error loading users:', error);
    }
  }

  async loadPolicyStats(): Promise<void> {
    try {
      // Clear existing stats first
      this.policyStats = [];
      
      const statsPromises = this.policies.map(async (policy) => {
        try {
          const stats = await this.policyAcknowledmentService.getPolicyAcknowledmentStats(policy.id);
          return stats;
        } catch (error) {
          console.error(`Error loading stats for policy ${policy.id}:`, error);
          // Return a default stats object if individual policy fails
          return {
            policy_id: policy.id,
            policy_name: policy.name,
            total_users: 0,
            acknowledged_count: 0,
            pending_count: 0,
            overdue_count: 0,
            acknowledgment_rate: 0,
            created_at: new Date().toISOString()
          };
        }
      });
      
      this.policyStats = await Promise.all(statsPromises);
    } catch (error) {
      console.error('Error loading policy stats:', error);
      this.policyStats = [];
    }
  }

  showToast(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    this.toastMessage = message;
    this.toastType = type;
    this.toastVisible = true;
  }

  openNotificationPopup(policy: Policy): void {
    this.selectedPolicy = policy;
    this.notificationFormData = {
      policy_id: policy.id,
      deadline_days: 5
    };
    this.notificationPopupVisible = true;
  }

  closeNotificationPopup(): void {
    this.notificationPopupVisible = false;
    this.selectedPolicy = null;
  }

  async sendNotifications(): Promise<void> {
    if (!this.selectedPolicy) return;

    try {
      const request: PolicyNotificationRequest = {
        policy_id: this.notificationFormData.policy_id,
        deadline_days: this.notificationFormData.deadline_days
      };

      const result = await this.policyAcknowledmentService.sendPolicyNotifications(request);
      this.showToast(`Notifications sent to ${result.notifications_sent} users`, 'success');
      this.closeNotificationPopup();
      await this.loadPolicyStats(); // Refresh stats
    } catch (error: any) {
      let errorMessage = 'Error sending notifications';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
  }

  async openDetailsPopup(stats: PolicyAcknowledmentStats): Promise<void> {
    this.selectedPolicyStats = stats;
    try {
      this.acknowledgmentDetails = await this.policyAcknowledmentService.getPolicyAcknowledments(stats.policy_id);
      this.detailsPopupVisible = true;
    } catch (error) {
      this.showToast('Error loading acknowledgment details', 'error');
    }
  }

  closeDetailsPopup(): void {
    this.detailsPopupVisible = false;
    this.selectedPolicyStats = null;
    this.acknowledgmentDetails = [];
  }

  getAcknowledmentRateColor(rate: number): string {
    if (rate >= 90) return '#28a745'; // Green
    if (rate >= 70) return '#ffc107'; // Yellow
    return '#dc3545'; // Red
  }

  getStatusColor(isAcknowledged: boolean, isOverdue: boolean): string {
    if (isAcknowledged) return '#28a745'; // Green
    if (isOverdue) return '#dc3545'; // Red
    return '#ffc107'; // Yellow
  }

  getStatusText(isAcknowledged: boolean, isOverdue: boolean): string {
    if (isAcknowledged) return 'Acknowledged';
    if (isOverdue) return 'Overdue';
    return 'Pending';
  }

  getStatusIcon(isAcknowledged: boolean, isOverdue: boolean): string {
    if (isAcknowledged) return 'check';
    if (isOverdue) return 'warning';
    return 'clock';
  }

  formatDate(date: string | Date): string {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleDateString('en-GB') + ' ' + d.toLocaleTimeString('en-GB', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  canManagePolicies(): boolean {
    return this.authService.isAdmin || this.authService.isHR;
  }

  async refreshData(): Promise<void> {
    await this.loadData();
    this.showToast('Data refreshed', 'success');
  }


  getPriorityClass(stats: PolicyAcknowledmentStats): string {
    if (stats.overdue_count > 0) return 'high-priority';
    if (stats.acknowledgment_rate < 70) return 'medium-priority';
    return 'normal-priority';
  }

  getComplianceStatus(stats: PolicyAcknowledmentStats): string {
    const rate = stats.acknowledgment_rate;
    if (rate >= 95) return 'Excellent';
    if (rate >= 85) return 'Good';
    if (rate >= 70) return 'Fair';
    return 'Poor';
  }

  getPolicyById(policyId: string): Policy | null {
    return this.policies.find(policy => policy.id === policyId) || null;
  }

  isOverdue(deadline?: string): boolean {
    if (!deadline) return false;
    return new Date() > new Date(deadline);
  }

  openNotificationForPolicy(policyId: string): void {
    const policy = this.getPolicyById(policyId);
    if (policy) {
      this.openNotificationPopup(policy);
    }
  }
}