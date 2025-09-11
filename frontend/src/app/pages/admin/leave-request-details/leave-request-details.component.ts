import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { LeaveService } from '../../../shared/services/leave.service';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxScrollViewModule } from 'devextreme-angular/ui/scroll-view';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxiItemModule } from 'devextreme-angular/ui/nested';
import { DxFileUploaderModule } from 'devextreme-angular/ui/file-uploader';
import { UserService } from '../../../shared/services/user.service';
import { AuthService } from '../../../shared/services/auth.service';

@Component({
  selector: 'app-leave-request-details',
  templateUrl: './leave-request-details.component.html',
  styleUrls: ['./leave-request-details.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxLoadIndicatorModule,
    DxButtonModule,
    DxFileUploaderModule,
    DxScrollViewModule,
    DxFormModule,
    DxiItemModule
  ]
})
export class LeaveRequestDetailsComponent implements OnInit {
  requestId: string | null = null;
  leaveRequest: any = null;
  documents: any[] = [];
  isLoading: boolean = false;
  isApproving: boolean = false;
  isRejecting: boolean = false;
  leaveRequestLeaveType: any = null;
  isLeaveRequestOwner: boolean = false;
  
  // Edit mode properties
  isEditMode: boolean = false;
  editData: any = {
    comments: ''
  };
  uploadedFiles: File[] = [];
  isSaving: boolean = false;
  
  // Approval properties
  approvalData: any = {
    approval_note: ''
  };

  private returnUrl: string = '/admin/leaves';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private leaveService: LeaveService,
    private userService: UserService,
    private authService: AuthService
  ) { 
    // Get the return URL from the query params, default to /admin/leaves
    this.route.queryParams.subscribe(params => {
      this.returnUrl = params['returnUrl'] || '/admin/leaves';
    });
  }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.requestId = params['id'];
      if (this.requestId) {
        this.loadRequestDetails();
      }
    });
  }

  async loadRequestDetails(): Promise<void> {
    if (!this.requestId) return;

    try {
      this.isLoading = true;
      this.leaveRequest = await this.leaveService.getLeaveRequestDetails(this.requestId);
      // Capitalize user name
      this.leaveRequest.user_name = this.capitalize(
        (await this.userService.getUserById(this.leaveRequest.user_id))?.name || ''
      );

      // Compute total_days = end_date - start_date + 1
      const start = new Date(this.leaveRequest.start_date);
      const end = new Date(this.leaveRequest.end_date);
      const msPerDay = 1000 * 60 * 60 * 24;

      const diffDays = Math.round((end.getTime() - start.getTime()) / msPerDay) + 1;
      this.leaveRequest.duration = diffDays;

      // Fetch leave type info
      this.leaveRequestLeaveType = (
        await this.leaveService.getLeaveTypes()
      ).find(type => type.id === this.leaveRequest.leave_type_id);

      // Load documents
      this.documents = await this.leaveService.getLeaveDocuments(this.requestId);
      // Validate and format document IDs
      this.documents = this.documents.map(doc => ({
        ...doc,
        file_name: doc.file_name || 'unknown-document'
      }));

      // Fetch decided_by info
      this.leaveRequest.decided_by = this.leaveRequest.decided_by ? this.capitalize((
        await this.userService.getUserById(this.leaveRequest.decided_by)
      )?.name || '') : null;

      // Format decided_at
      this.leaveRequest.decision_at = this.leaveRequest.decision_at ? new Date(this.leaveRequest.decision_at).toLocaleString() : null;

      // Check if the user is the owner of the leave request
      this.isLeaveRequestOwner = this.leaveRequest.user_id === (await this.authService.getUser()).data?.id;
      
      // Initialize edit data
      this.editData.comments = this.leaveRequest.comments || '';
    } catch (error) {
      console.error('Error loading leave request details:', error);
    } finally {
      this.isLoading = false;
    }
  }

  async approveRequest(): Promise<void> {
    if (!this.requestId) return;

    try {
      this.isApproving = true;
      await this.leaveService.approveLeaveRequest(this.requestId, this.approvalData.approval_note);
      await this.loadRequestDetails();
      this.router.navigate([this.returnUrl]);
    } catch (error) {
      console.error('Error approving leave request:', error);
    } finally {
      this.isApproving = false;
    }
  }

  async rejectRequest(): Promise<void> {
    if (!this.requestId) return;
    try {
      this.isRejecting = true;
      await this.leaveService.rejectLeaveRequest(this.requestId, this.approvalData.approval_note);
      await this.loadRequestDetails();
      this.router.navigate([this.returnUrl]);
    } catch (error) {
      console.error('Error rejecting leave request:', error);
      // Log more details about the error
    } finally {
      this.isRejecting = false;
    }
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'pending': return 'status-pending';
      case 'approved': return 'status-approved';
      case 'rejected': return 'status-rejected';
      default: return '';
    }
  }

  capitalize(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
  
  toggleEditMode(): void {
    this.isEditMode = !this.isEditMode;
    
    if (this.isEditMode) {
      // Initialize edit data when entering edit mode
      this.editData.comments = this.leaveRequest.comments || '';
      this.uploadedFiles = [];
      
      // Refresh document list when entering edit mode
      if (this.requestId) {
        this.refreshDocumentList();
      }
    } else {
      // Reset edit data when canceling edit mode
      this.editData.comments = this.leaveRequest.comments || '';
      this.uploadedFiles = [];
    }
  }
  
  async refreshDocumentList(): Promise<void> {
    if (!this.requestId) return;
    
    try {
      this.documents = await this.leaveService.getLeaveDocuments(this.requestId);
    } catch (error) {
      console.error('Error refreshing document list:', error);
    }
  }
  
  onFileUploaded(e: any): void {
    if (e.value && e.value.length > 0) {
      this.uploadedFiles = e.value;
    }
  }
  
  async removeDocument(documentId: string): Promise<void> {
    // Basic validation
    if (!this.requestId || !documentId) {
      return;
    }
    
    const docToDelete = this.documents.find(doc => doc.document_id === documentId);
    if (!docToDelete) return;
    
    try {
      // Call the service method to delete
      await this.leaveService.deleteLeaveDocument(this.requestId, documentId);
      
      // Reload documents list
      await this.refreshDocumentList();
    } catch (error) {
      console.error('Failed to delete document:', error);
    }
  }
  
  async downloadDocument(documentId: string, fileName: string = 'document'): Promise<void> {
    if (!this.requestId || !documentId) return;
    
    try {
      const blob = await this.leaveService.downloadLeaveDocumentFromFiles(this.requestId, documentId);
      
      if (!blob || blob.size === 0) return;
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName || 'document';
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }, 100);
    } catch (error) {
      console.error('Error downloading document:', error);
    }
  }
  
  async saveChanges(): Promise<void> {
    if (!this.requestId || this.isSaving) return;
    this.isSaving = true;
    
    try {     
      // 1. Update leave request comments
      const updateData = {
        comments: this.editData.comments
      };
      
      const updateResult = await this.leaveService.updateLeaveRequest(this.requestId, updateData);
      
      // 2. Upload any new files
      if (this.uploadedFiles.length > 0) {
        for (const file of this.uploadedFiles) {
          try {
            const uploadResult = await this.leaveService.uploadFile(this.requestId, file);
          } catch (uploadError) {
            console.error(`Error uploading file ${file.name}:`, uploadError);
          }
        }
      }
      
      // 3. Exit edit mode and reload data
      this.isEditMode = false;
      await this.loadRequestDetails();
    } catch (error) {
      console.error('Error updating leave request:', error);
      alert('There was an error saving your changes. Please try again.');
    } finally {
      this.isSaving = false;
    }
  }
}
