import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxToastModule } from 'devextreme-angular/ui/toast';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxiItemModule, DxoLabelModule, DxiColumnModule } from 'devextreme-angular/ui/nested';
import { RouterModule, Router } from '@angular/router';
import { PolicyService, Policy } from '../../shared/services/policy.service';
import { PolicyAcknowledmentService, UserPolicyStatus } from '../../shared/services/policy-acknowledgment.service';
import { AuthService } from '../../shared/services/auth.service';
import { DocumentViewerComponent } from '../../shared/components/document-viewer/document-viewer.component';

@Component({
  selector: 'app-user-policies',
  templateUrl: './user-policies.component.html',
  styleUrls: ['./user-policies.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxDataGridModule,
    DxButtonModule,
    DxToastModule,
    DxPopupModule,
    DxiItemModule,
    DxoLabelModule,
    DxiColumnModule,
    RouterModule,
    DocumentViewerComponent
  ]
})
export class UserPoliciesComponent implements OnInit, OnDestroy {
  userPolicies: UserPolicyStatus[] = [];
  loading = false;
  toastVisible = false;
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' | 'warning' = 'info';
  
  // Document viewer
  documentViewerVisible = false;
  currentDocumentUrl = '';
  currentDocumentName = '';
  currentDocumentType = '';
  
  // Acknowledgment popup
  acknowledgmentPopupVisible = false;
  selectedPolicy: UserPolicyStatus | null = null;
  
  // Current user info
  currentUser: any = null;

  constructor(
    private policyService: PolicyService,
    private policyAcknowledmentService: PolicyAcknowledmentService,
    private authService: AuthService,
    private router: Router
  ) {}

  async ngOnInit(): Promise<void> {
    await this.loadCurrentUser();
    await this.loadUserPolicies();
  }

  ngOnDestroy(): void {
    // Cleanup if needed
  }

  async loadCurrentUser(): Promise<void> {
    try {
      const userResult = await this.authService.getUser();
      if (userResult.isOk && userResult.data) {
        this.currentUser = userResult.data;
      }
    } catch (error) {
      // Error loading current user - handled silently
    }
  }

  async loadUserPolicies(): Promise<void> {
    this.loading = true;
    try {
      // Clear existing data first
      this.userPolicies = [];
      
      // Load fresh data
      const policies = await this.policyAcknowledmentService.getUserPolicyStatus();
      this.userPolicies = policies || [];
      
      if (this.userPolicies.length === 0) {
        // No policies found - this is normal for some users
      }
    } catch (error) {
      console.error('Error loading policies:', error);
      this.showToast('Error loading policies', 'error');
      this.userPolicies = [];
    } finally {
      this.loading = false;
    }
  }

  showToast(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    this.toastMessage = message;
    this.toastType = type;
    this.toastVisible = true;
  }

  async downloadPolicy(policy: UserPolicyStatus): Promise<void> {
    try {
      await this.policyService.downloadPolicy(policy.policy_id, policy.file_name);
      this.showToast(`Downloaded ${policy.file_name}`, 'success');
    } catch (error: any) {
      let errorMessage = 'Error downloading policy';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
  }

  viewPolicy(policy: UserPolicyStatus): void {
    // Reset state first
    this.closeDocumentViewer();
    
    // Set new document data
    setTimeout(() => {
      this.currentDocumentUrl = this.policyService.getPolicyViewUrl(policy.policy_id);
      this.currentDocumentName = policy.file_name;
      this.currentDocumentType = policy.file_type;
      this.documentViewerVisible = true;
    }, 100);
  }

  openAcknowledmentPopup(policy: UserPolicyStatus): void {
    this.selectedPolicy = policy;
    this.acknowledgmentPopupVisible = true;
  }

  closeAcknowledmentPopup(): void {
    this.acknowledgmentPopupVisible = false;
    this.selectedPolicy = null;
  }

  async acknowledgePolicy(): Promise<void> {
    if (!this.selectedPolicy || !this.currentUser) {
      return;
    }

    try {
      await this.policyAcknowledmentService.acknowledgePolicy({
        policy_id: this.selectedPolicy.policy_id,
        user_id: this.currentUser.id,
        signature_method: 'click_acknowledgment'
      });

      this.showToast('Policy acknowledged successfully', 'success');
      this.closeAcknowledmentPopup();
      await this.loadUserPolicies(); // Refresh the list
    } catch (error: any) {
      let errorMessage = 'Error acknowledging policy';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
  }

  onRowClick(event: any): void {
    // Get the policy data from the clicked row
    const policy = event.data;
    if (policy) {
      this.viewPolicy(policy);
    }
  }

  closeDocumentViewer(): void {
    this.documentViewerVisible = false;
    this.currentDocumentUrl = '';
    this.currentDocumentName = '';
    this.currentDocumentType = '';
  }

  formatDate(date: string | Date): string {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleDateString('en-GB') + ' ' + d.toLocaleTimeString('en-GB', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  getFileIcon(fileType: string): string {
    return this.policyService.getFileIcon(fileType);
  }

  getFileTypeColor(fileType: string): string {
    return this.policyService.getFileTypeColor(fileType);
  }

  getStatusColor(policy: UserPolicyStatus): string {
    return this.policyAcknowledmentService.getStatusColor(policy);
  }

  getStatusText(policy: UserPolicyStatus): string {
    return this.policyAcknowledmentService.getStatusText(policy);
  }

  getStatusIcon(policy: UserPolicyStatus): string {
    return this.policyAcknowledmentService.getStatusIcon(policy);
  }

  getDaysRemainingText(policy: UserPolicyStatus): string {
    if (policy.is_acknowledged) return 'Completed';
    if (policy.is_overdue) return 'Overdue';
    if (policy.days_remaining !== null && policy.days_remaining !== undefined) {
      return `${policy.days_remaining} days left`;
    }
    return 'No deadline';
  }

  canAcknowledge(policy: UserPolicyStatus): boolean {
    return !policy.is_acknowledged;
  }

  getPriorityClass(policy: UserPolicyStatus): string {
    if (policy.is_acknowledged) return 'acknowledged';
    if (policy.is_overdue) return 'overdue';
    if (policy.days_remaining !== null && policy.days_remaining !== undefined && policy.days_remaining <= 2) return 'urgent';
    return 'normal';
  }
}