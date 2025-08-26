import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxToastModule } from 'devextreme-angular/ui/toast';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxFileUploaderModule } from 'devextreme-angular/ui/file-uploader';
import { DxSelectBoxModule } from 'devextreme-angular/ui/select-box';
import { DxTextAreaModule } from 'devextreme-angular/ui/text-area';
import { DxTextBoxModule } from 'devextreme-angular/ui/text-box';
import { DxiItemModule, DxoLabelModule, DxiColumnModule } from 'devextreme-angular/ui/nested';
import { PolicyService, Policy, PolicyCreate, PolicyUpdate } from '../../../shared/services/policy.service';
import { AuthService } from '../../../shared/services/auth.service';
import { OrgUnitService } from '../../../shared/services/org-unit.service';
import { DocumentViewerComponent } from '../../../shared/components/document-viewer/document-viewer.component';

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
    DxPopupModule,
    DxFormModule,
    DxFileUploaderModule,
    DxSelectBoxModule,
    DxTextAreaModule,
    DxTextBoxModule,
    DxiItemModule,
    DxoLabelModule,
    DxiColumnModule,
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
  
  // Add/Edit popup
  addEditPopupVisible = false;
  isEditMode = false;
  selectedPolicy: Policy | null = null;
  
  // Form data
  formData: any = {
    name: '',
    description: '',
    org_unit_id: null
  };
  
  selectedFile: File | null = null;
  
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
    private orgUnitService: OrgUnitService
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
      this.policies = await this.policyService.getPolicies();
    } catch (error) {
      this.showToast('Error loading policies', 'error');
    } finally {
      this.loading = false;
    }
  }

  showToast(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    this.toastMessage = message;
    this.toastType = type;
    this.toastVisible = true;
  }

  canManagePolicies(): boolean {
    return this.isAdmin || this.isHR || this.isManager;
  }

  canDeletePolicy(): boolean {
    return this.isAdmin || this.isHR;
  }

  openAddPolicyPopup(): void {
    if (!this.canManagePolicies()) {
      this.showToast('You do not have permission to add policies', 'error');
      return;
    }
    
    this.isEditMode = false;
    this.selectedPolicy = null;
    this.formData = {
      name: '',
      description: '',
      org_unit_id: null
    };
    this.selectedFile = null;
    this.addEditPopupVisible = true;
  }

  openEditPolicyPopup(policy: Policy): void {
    if (!this.canManagePolicies()) {
      this.showToast('You do not have permission to edit policies', 'error');
      return;
    }
    
    this.isEditMode = true;
    this.selectedPolicy = policy;
    this.formData = {
      name: policy.name,
      description: policy.description || '',
      org_unit_id: policy.org_unit_id || null
    };
    this.selectedFile = null;
    this.addEditPopupVisible = true;
  }

  closeAddEditPopup(): void {
    this.addEditPopupVisible = false;
    this.selectedPolicy = null;
    this.formData = {
      name: '',
      description: '',
      org_unit_id: null
    };
    this.selectedFile = null;
  }

  onFileSelected(event: any): void {
    const files = event.value;
    if (files && files.length > 0) {
      this.selectedFile = files[0];
    }
  }

  async savePolicy(): Promise<void> {
    if (!this.formData.name?.trim()) {
      this.showToast('Policy name is required', 'error');
      return;
    }

    if (!this.isEditMode && !this.selectedFile) {
      this.showToast('Please select a file to upload', 'error');
      return;
    }

    try {
      if (this.isEditMode && this.selectedPolicy) {
        // Update existing policy
        const updateData: PolicyUpdate = {
          name: this.formData.name.trim(),
          description: this.formData.description?.trim() || undefined,
          org_unit_id: this.formData.org_unit_id || undefined
        };
        
        await this.policyService.updatePolicy(this.selectedPolicy.id, updateData);
        this.showToast('Policy updated successfully', 'success');
      } else {
        // Create new policy
        const createData: PolicyCreate = {
          name: this.formData.name.trim(),
          description: this.formData.description?.trim() || undefined,
          org_unit_id: this.formData.org_unit_id || undefined
        };
        
        await this.policyService.createPolicy(createData, this.selectedFile!);
        this.showToast('Policy created successfully', 'success');
      }
      
      this.closeAddEditPopup();
      await this.loadPolicies();
    } catch (error: any) {
      let errorMessage = this.isEditMode ? 'Error updating policy' : 'Error creating policy';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
  }

  async deletePolicy(policy: Policy): Promise<void> {
    if (!this.canDeletePolicy()) {
      this.showToast('You do not have permission to delete policies', 'error');
      return;
    }

    if (!confirm(`Are you sure you want to delete the policy "${policy.name}"?`)) {
      return;
    }

    try {
      await this.policyService.deletePolicy(policy.id);
      this.showToast('Policy deleted successfully', 'success');
      await this.loadPolicies();
    } catch (error: any) {
      let errorMessage = 'Error deleting policy';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
  }

  async downloadPolicy(policy: Policy): Promise<void> {
    try {
      await this.policyService.downloadPolicy(policy.id, policy.file_name);
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

  viewPolicy(policy: Policy): void {
    try {
      // Reset state first
      this.closeDocumentViewer();
      
      // Set new document data
      setTimeout(() => {
        try {
          this.currentDocumentUrl = this.policyService.getPolicyViewUrl(policy.id);
          this.currentDocumentName = policy.file_name;
          this.currentDocumentType = policy.file_type;
          this.documentViewerVisible = true;
        } catch (error) {
          this.showToast('Error preparing document for viewing. Please try downloading instead.', 'error');
        }
      }, 100);
    } catch (error) {
      this.showToast('Error opening document viewer', 'error');
    }
  }

  closeDocumentViewer(): void {
    this.documentViewerVisible = false;
    this.currentDocumentUrl = '';
    this.currentDocumentName = '';
    this.currentDocumentType = '';
  }

  // File uploader configuration
  fileUploaderOptions = {
    multiple: false,
    accept: '.pdf',
    uploadMode: 'useButtons' as any,
    showFileList: true,
    labelText: 'Drop a PDF file here or click to browse...',
    selectButtonText: 'Select PDF File',
    uploadButtonText: 'Upload'
  };
}