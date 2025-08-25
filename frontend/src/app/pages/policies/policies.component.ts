import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxToastModule } from 'devextreme-angular/ui/toast';
import { DxSelectBoxModule } from 'devextreme-angular/ui/select-box';
import { DxiItemModule, DxoLabelModule, DxiColumnModule } from 'devextreme-angular/ui/nested';
import { RouterModule, Router } from '@angular/router';
import { PolicyService, Policy } from '../../shared/services/policy.service';
import { AuthService } from '../../shared/services/auth.service';
import { OrgUnitService } from '../../shared/services/org-unit.service';
import { DocumentViewerComponent } from '../../shared/components/document-viewer/document-viewer.component';

@Component({
  selector: 'app-policies',
  templateUrl: './policies.component.html',
  styleUrls: ['./policies.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxDataGridModule,
    DxButtonModule,
    DxToastModule,
    DxSelectBoxModule,
    DxiItemModule,
    DxoLabelModule,
    DxiColumnModule,
    RouterModule,
    DocumentViewerComponent
  ]
})
export class PoliciesComponent implements OnInit {
  policies: Policy[] = [];
  orgUnits: any[] = [];
  loading = false;
  toastVisible = false;
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' | 'warning' = 'info';
  
  selectedOrgUnitId: string | null = null;
  
  // Document viewer
  documentViewerVisible = false;
  currentDocumentUrl = '';
  currentDocumentName = '';
  currentDocumentType = '';
  
  // Current user info
  currentUser: any = null;
  isAdmin = false;
  isHR = false;
  isManager = false;

  constructor(
    private policyService: PolicyService,
    private authService: AuthService,
    private orgUnitService: OrgUnitService,
    private router: Router
  ) {}

  async ngOnInit(): Promise<void> {
    await this.loadCurrentUser();
    await this.loadOrgUnits();
    await this.loadPolicies();
  }

  async loadCurrentUser(): Promise<void> {
    try {
      const userResult = await this.authService.getUser();
      if (userResult.isOk && userResult.data) {
        this.currentUser = userResult.data;
        this.isAdmin = this.authService.isAdmin;
        this.isHR = this.authService.isHR;
        this.isManager = this.authService.isManager;
      }
    } catch (error) {
      // Error loading current user - handled silently
    }
  }

  async loadOrgUnits(): Promise<void> {
    try {
      const orgUnitsObservable = this.orgUnitService.getOrgUnits();
      this.orgUnits = await new Promise((resolve, reject) => {
        orgUnitsObservable.subscribe({
          next: (data) => resolve(data),
          error: (error) => reject(error)
        });
      });
      // Add "All Organizations" option
      this.orgUnits.unshift({
        id: null,
        name: 'All Organizations'
      });
    } catch (error) {
      // Error loading org units - handled silently
    }
  }

  async loadPolicies(): Promise<void> {
    this.loading = true;
    try {
      this.policies = await this.policyService.getPolicies(this.selectedOrgUnitId || undefined);
    } catch (error) {
      this.showToast('Error loading policies', 'error');
    } finally {
      this.loading = false;
    }
  }

  async onOrgUnitFilterChanged(event: any): Promise<void> {
    this.selectedOrgUnitId = event.value;
    await this.loadPolicies();
  }

  showToast(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    this.toastMessage = message;
    this.toastType = type;
    this.toastVisible = true;
  }

  async downloadPolicy(policy: Policy): Promise<void> {
    try {
      await this.policyService.downloadPolicy(policy.id, policy.file_name);
      this.showToast(`Downloaded ${policy.file_name}`, 'success');
    } catch (error: any) {
      let errorMessage = 'Error downloading policy';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
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

  getOrgUnitDisplayName(orgUnitName?: string): string {
    return orgUnitName || 'All Organizations';
  }

  canManagePolicies(): boolean {
    return this.isAdmin || this.isHR || this.isManager;
  }

  navigateToManagePolicies(): void {
    this.router.navigate(['/admin/policies']);
  }

  viewPolicy(policy: Policy): void {
    // Reset state first
    this.closeDocumentViewer();
    
    // Set new document data
    setTimeout(() => {
      this.currentDocumentUrl = this.policyService.getPolicyViewUrl(policy.id);
      this.currentDocumentName = policy.file_name;
      this.currentDocumentType = policy.file_type;
      this.documentViewerVisible = true;
    }, 100);
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
}