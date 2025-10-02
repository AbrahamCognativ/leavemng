import { Component, OnInit, ViewChild, ElementRef, ChangeDetectorRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxFileUploaderModule } from 'devextreme-angular/ui/file-uploader';
import { DxSelectBoxModule } from 'devextreme-angular/ui/select-box';
import { DxTextAreaModule } from 'devextreme-angular/ui/text-area';
import { DxTextBoxModule } from 'devextreme-angular/ui/text-box';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxiItemModule, DxoLabelModule, DxiColumnModule, DxoPagingModule, DxoPagerModule, DxoSearchPanelModule, DxoHeaderFilterModule, DxoFilterRowModule, DxoExportModule } from 'devextreme-angular/ui/nested';
import { UserDocumentsService, UserDocument, UserDocumentCreate, BulkUploadResult } from '../../../shared/services/user-documents.service';
import { AuthService } from '../../../shared/services/auth.service';
import { UserService } from '../../../shared/services/user.service';
import { DocumentViewerComponent } from '../../../shared/components/document-viewer/document-viewer.component';
import notify from 'devextreme/ui/notify';

@Component({
  selector: 'app-user-documents',
  templateUrl: './user-documents.component.html',
  styleUrls: ['./user-documents.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxDataGridModule,
    DxButtonModule,
    DxPopupModule,
    DxFormModule,
    DxFileUploaderModule,
    DxSelectBoxModule,
    DxTextAreaModule,
    DxTextBoxModule,
    DxLoadIndicatorModule,
    DxiItemModule,
    DxoLabelModule,
    DxiColumnModule,
    DxoPagingModule,
    DxoPagerModule,
    DxoSearchPanelModule,
    DxoHeaderFilterModule,
    DxoFilterRowModule,
    DxoExportModule,
    DocumentViewerComponent
  ]
})
export class UserDocumentsComponent implements OnInit, AfterViewChecked {
  users: any[] = [];
  usersWithAllOption: any[] = [];
  userDocuments: UserDocument[] = [];
  allDocuments: UserDocument[] = [];
  loading = false;
  loadingDocuments = false;
  uploading = false;
  
  // User documents popup
  userDocumentsPopupVisible = false;
  selectedUser: any = null;
  
  // Upload popup
  uploadPopupVisible = false;
  
  // Bulk payslip upload popup
  bulkPayslipPopupVisible = false;
  bulkUploading = false;
  selectedPayslipFiles: File[] = [];
  bulkUploadResult: BulkUploadResult | null = null;
  
  // Manual match popup
  manualMatchPopupVisible = false;
  selectedFailedDocument: any = null;
  manualMatching = false;
  manualMatchFormData: any = {
    user_id: null,
    document_title: '',
    description: ''
  };
  
  // Failed document files storage (for preview)
  failedDocumentFiles: Map<string, File> = new Map();
  
  // ViewChild for scrollable content
  @ViewChild('scrollableContent') scrollableContent!: ElementRef;
  
  
  // Flag to trigger scroll after view update
  shouldScrollToResults = false;
  
  // Form data
  formData: any = {
    user_id: null,
    title: '',
    description: ''
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
    private userDocumentsService: UserDocumentsService,
    private authService: AuthService,
    private userService: UserService,
    private cdr: ChangeDetectorRef
  ) {}

  async ngOnInit(): Promise<void> {
    await this.loadCurrentUser();
    await this.loadUsers();
    await this.loadAllDocuments();
  }

  ngAfterViewChecked(): void {
    if (this.shouldScrollToResults && this.bulkUploadResult) {
      this.shouldScrollToResults = false;
      this.performScroll();
    }
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

  async loadUsers(): Promise<void> {
    this.loading = true;
    try {
      const usersObservable = this.userService.getUsers();
      this.users = await new Promise((resolve, reject) => {
        usersObservable.subscribe({
          next: (data) => {
            // Define system user emails to exclude
            const systemUserEmails = [
              'scheduler@cognativ.com',
              'user@example.com'
            ];
            
            // Filter out system users and add display_name
            const filteredUsers = data
              .filter((user: any) => {
                // Exclude users with emails containing 'system' or specific system user emails
                return !user.email?.includes('system') &&
                       !systemUserEmails.includes(user.email?.toLowerCase());
              })
              .map((user: any) => ({
                ...user,
                display_name: `${user.name || (user.first_name + ' ' + user.last_name)} (${user.email})`
              }));
            resolve(filteredUsers);
          },
          error: (error) => reject(error)
        });
      });
      
      // Create users list with "All Users" option
      this.usersWithAllOption = [
        {
          id: 'ALL_USERS',
          display_name: '📢 All Users',
          email: 'all_users',
          name: 'All Users'
        },
        ...this.users
      ];
    } catch (error) {
      this.showToast('Error loading users', 'error');
    } finally {
      this.loading = false;
    }
  }

  async loadAllDocuments(): Promise<void> {
    try {
      this.allDocuments = await this.userDocumentsService.getUserDocuments();
    } catch (error) {
      this.showToast('Error loading documents', 'error');
    }
  }

  getUserDocumentCount(userId: string): number {
    return this.allDocuments.filter(doc => doc.user_id === userId).length;
  }

  async viewUserDocuments(user: any): Promise<void> {
    this.selectedUser = user;
    this.loadingDocuments = true;
    this.userDocumentsPopupVisible = true;
    
    try {
      this.userDocuments = await this.userDocumentsService.getUserDocuments(user.id);
    } catch (error) {
      this.showToast('Error loading user documents', 'error');
    } finally {
      this.loadingDocuments = false;
    }
  }

  closeUserDocumentsPopup(): void {
    this.userDocumentsPopupVisible = false;
    this.selectedUser = null;
    this.userDocuments = [];
  }

  openUploadPopup(): void {
    this.formData = {
      user_id: null,
      title: '',
      description: ''
    };
    this.selectedFile = null;
    this.uploadPopupVisible = true;
  }

  openUploadPopupForUser(user: any): void {
    this.formData = {
      user_id: user.id,
      title: '',
      description: ''
    };
    this.selectedFile = null;
    this.uploadPopupVisible = true;
  }

  closeUploadPopup(): void {
    this.uploadPopupVisible = false;
    this.formData = {
      user_id: null,
      title: '',
      description: ''
    };
    this.selectedFile = null;
  }

  openBulkPayslipPopup(): void {
    this.selectedPayslipFiles = [];
    this.bulkUploadResult = null;
    this.bulkPayslipPopupVisible = true;
  }

  closeBulkPayslipPopup(): void {
    this.bulkPayslipPopupVisible = false;
    this.selectedPayslipFiles = [];
    this.bulkUploadResult = null;
  }

  onFileSelected(event: any): void {
    const files = event.value;
    if (files && files.length > 0) {
      this.selectedFile = files[0];
    }
  }

  onPayslipFilesSelected(event: any): void {
    const files = event.value;
    if (files && files.length > 0) {
      this.selectedPayslipFiles = Array.from(files);
    }
  }

  async uploadDocument(): Promise<void> {
    if (!this.formData.user_id) {
      this.showToast('Please select a user', 'error');
      return;
    }

    if (!this.formData.title?.trim()) {
      this.showToast('Document title is required', 'error');
      return;
    }

    if (!this.selectedFile) {
      this.showToast('Please select a file to upload', 'error');
      return;
    }

    this.uploading = true;
    try {
      // Check if "All Users" is selected
      if (this.formData.user_id === 'ALL_USERS') {
        await this.uploadDocumentToAllUsers();
      } else {
        await this.uploadDocumentToSingleUser();
      }
      
      this.closeUploadPopup();
      await this.loadAllDocuments();
    } catch (error: any) {
      let errorMessage = 'Error uploading document';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    } finally {
      this.uploading = false;
    }
  }

  private async uploadDocumentToSingleUser(): Promise<void> {
    if (!this.selectedFile) {
      throw new Error('No file selected');
    }
    
    const createData: UserDocumentCreate = {
      name: this.formData.title.trim(),
      description: this.formData.description?.trim() || undefined,
      user_id: this.formData.user_id,
      send_email_notification: true
    };
    
    await this.userDocumentsService.createUserDocument(createData, this.selectedFile);
    this.showToast('Document uploaded successfully', 'success');
  }

  private async uploadDocumentToAllUsers(): Promise<void> {
    if (!this.selectedFile) {
      throw new Error('No file selected');
    }
    
    let successCount = 0;
    let errorCount = 0;
    
    // Upload document for each user
    for (const user of this.users) {
      try {
        const createData: UserDocumentCreate = {
          name: this.formData.title.trim(),
          description: this.formData.description?.trim() || undefined,
          user_id: user.id,
          send_email_notification: true
        };
        
        await this.userDocumentsService.createUserDocument(createData, this.selectedFile);
        successCount++;
      } catch (error) {
        errorCount++;
        console.error(`Failed to upload document for user ${user.email}:`, error);
      }
    }
    
    if (errorCount === 0) {
      this.showToast(`Document uploaded successfully to all ${successCount} users`, 'success');
    } else if (successCount > 0) {
      this.showToast(`Document uploaded to ${successCount} users, ${errorCount} failed`, 'warning');
    } else {
      this.showToast('Failed to upload document to any users', 'error');
    }
  }

  async uploadBulkPayslips(): Promise<void> {
    if (!this.selectedPayslipFiles || this.selectedPayslipFiles.length === 0) {
      this.showToast('Please select PDF files to upload', 'error');
      return;
    }

    // Validate all files are PDFs
    const nonPdfFiles = this.selectedPayslipFiles.filter(file => !file.name.toLowerCase().endsWith('.pdf'));
    if (nonPdfFiles.length > 0) {
      this.showToast(`Only PDF files are supported. Found non-PDF files: ${nonPdfFiles.map(f => f.name).join(', ')}`, 'error');
      return;
    }

    this.bulkUploading = true;
    try {
      // Store files for potential preview later
      this.selectedPayslipFiles.forEach(file => {
        this.failedDocumentFiles.set(file.name, file);
      });

      this.bulkUploadResult = await this.userDocumentsService.bulkPayslipUpload(
        this.selectedPayslipFiles,
        'payslip',
        true
      );

      // Show summary toast
      if (this.bulkUploadResult.successful_uploads > 0) {
        this.showToast(this.bulkUploadResult.summary, 'success');
      } else {
        this.showToast(this.bulkUploadResult.summary, 'warning');
      }

      // Refresh documents list
      await this.loadAllDocuments();
      
      // Trigger scroll after view update
      this.shouldScrollToResults = true;
      this.cdr.detectChanges();

    } catch (error: any) {
      let errorMessage = 'Error processing payslip files';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    } finally {
      this.bulkUploading = false;
    }
  }

  previewFailedDocument(failedDoc: any): void {
    try {
      const file = this.failedDocumentFiles.get(failedDoc.file_name);
      if (!file) {
        this.showToast('Document file not available for preview', 'error');
        return;
      }

      // Create a blob URL for the file
      const blob = new Blob([file], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);

      // Reset state first
      this.closeDocumentViewer();
      
      // Set new document data
      setTimeout(() => {
        try {
          this.currentDocumentUrl = url;
          this.currentDocumentName = failedDoc.file_name;
          this.currentDocumentType = 'pdf';
          this.documentViewerVisible = true;
        } catch (error) {
          this.showToast('Error preparing document for viewing', 'error');
        }
      }, 100);
    } catch (error) {
      this.showToast('Error opening document viewer', 'error');
    }
  }

  openManualMatchPopup(failedDoc: any): void {
    this.selectedFailedDocument = failedDoc;
    this.manualMatchFormData = {
      user_id: null,
      document_title: `Payslip - ${failedDoc.file_name}`,
      description: `Manual assignment for ${failedDoc.file_name}${failedDoc.extracted_ids?.length > 0 ? ` (IDs found: ${failedDoc.extracted_ids.join(', ')})` : ''}`
    };
    this.manualMatchPopupVisible = true;
  }

  closeManualMatchPopup(): void {
    this.manualMatchPopupVisible = false;
    this.selectedFailedDocument = null;
    this.manualMatchFormData = {
      user_id: null,
      document_title: '',
      description: ''
    };
  }

  async assignDocumentManually(): Promise<void> {
    if (!this.selectedFailedDocument || !this.manualMatchFormData.user_id || !this.manualMatchFormData.document_title) {
      this.showToast('Please fill in all required fields', 'error');
      return;
    }

    const file = this.failedDocumentFiles.get(this.selectedFailedDocument.file_name);
    if (!file) {
      this.showToast('Document file not available for assignment', 'error');
      return;
    }

    this.manualMatching = true;
    try {
      const createData = {
        name: this.manualMatchFormData.document_title.trim(),
        description: this.manualMatchFormData.description?.trim() || undefined,
        user_id: this.manualMatchFormData.user_id,
        document_type: 'payslip',
        send_email_notification: true
      };

      // Create the document
      const createdDocument = await this.userDocumentsService.createUserDocument(createData, file);
      
      // Update the bulk upload result to reflect the manual assignment
      if (this.bulkUploadResult) {
        const docIndex = this.bulkUploadResult.processing_details.findIndex(
          doc => doc.file_name === this.selectedFailedDocument.file_name
        );
        if (docIndex !== -1) {
          // Store the original status for counter updates
          const originalStatus = this.bulkUploadResult.processing_details[docIndex].status;
          
          // Update the document status
          this.bulkUploadResult.processing_details[docIndex].status = 'success';
          this.bulkUploadResult.processing_details[docIndex].error_message = undefined;
          this.bulkUploadResult.processing_details[docIndex].document_id = createdDocument.id;
          
          // Find the assigned user
          const assignedUser = this.users.find(user => user.id === this.manualMatchFormData.user_id);
          if (assignedUser) {
            this.bulkUploadResult.processing_details[docIndex].matched_user = {
              id: assignedUser.id,
              name: assignedUser.name || `${assignedUser.first_name} ${assignedUser.last_name}`,
              email: assignedUser.email,
              passport_or_id_number: assignedUser.passport_or_id_number || 'Manual Assignment'
            };
          }
          
          // Update counters based on original status
          this.bulkUploadResult.successful_uploads++;
          if (originalStatus === 'no_user_found') {
            this.bulkUploadResult.no_user_found = Math.max(0, this.bulkUploadResult.no_user_found - 1);
          } else if (originalStatus === 'no_id_found') {
            this.bulkUploadResult.no_id_extracted = Math.max(0, this.bulkUploadResult.no_id_extracted - 1);
          } else if (originalStatus === 'failed') {
            this.bulkUploadResult.failed_uploads = Math.max(0, this.bulkUploadResult.failed_uploads - 1);
          }
          
          // Update summary message
          const totalProcessed = this.bulkUploadResult.successful_uploads + this.bulkUploadResult.failed_uploads +
                               this.bulkUploadResult.no_user_found + this.bulkUploadResult.no_id_extracted;
          this.bulkUploadResult.summary = `Processed ${totalProcessed} files: ${this.bulkUploadResult.successful_uploads} successful, ` +
                                        `${this.bulkUploadResult.failed_uploads} failed, ${this.bulkUploadResult.no_user_found} no user found, ` +
                                        `${this.bulkUploadResult.no_id_extracted} no ID extracted`;
        }
      }
      
      // Remove the file from failed documents storage since it's now processed
      this.failedDocumentFiles.delete(this.selectedFailedDocument.file_name);
      
      // Refresh documents list
      await this.loadAllDocuments();
      
      this.showToast('Document assigned successfully', 'success');
      this.closeManualMatchPopup();

    } catch (error: any) {
      console.error('Error assigning document:', error);
      let errorMessage = 'Error assigning document';
      
      // Handle different types of errors
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      } else if (error?.message) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      }
      
      this.showToast(errorMessage, 'error');
    } finally {
      this.manualMatching = false;
    }
  }

  getStatusIcon(status: string): string {
    switch (status) {
      case 'success': return 'check';
      case 'failed': return 'close';
      case 'no_id_found': return 'warning';
      case 'no_user_found': return 'user';
      default: return 'help';
    }
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'success': return '#28a745';
      case 'failed': return '#dc3545';
      case 'no_id_found': return '#ffc107';
      case 'no_user_found': return '#17a2b8';
      default: return '#6c757d';
    }
  }

  async deleteDocument(document: UserDocument): Promise<void> {
    if (!confirm(`Are you sure you want to delete "${document.name}"?`)) {
      return;
    }

    try {
      await this.userDocumentsService.deleteUserDocument(document.id);
      this.showToast('Document deleted successfully', 'success');
      
      // Refresh both the user documents and all documents
      await this.loadAllDocuments();
      if (this.selectedUser) {
        this.userDocuments = await this.userDocumentsService.getUserDocuments(this.selectedUser.id);
      }
    } catch (error: any) {
      let errorMessage = 'Error deleting document';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
  }

  async downloadDocument(document: UserDocument): Promise<void> {
    try {
      await this.userDocumentsService.downloadDocument(document.id, document.file_name);
    } catch (error: any) {
      let errorMessage = 'Error downloading document';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
  }

  viewDocument(document: UserDocument): void {
    try {
      // Reset state first
      this.closeDocumentViewer();
      
      // Set new document data
      setTimeout(() => {
        try {
          this.currentDocumentUrl = this.userDocumentsService.getDocumentViewUrl(document.id);
          this.currentDocumentName = document.file_name;
          this.currentDocumentType = document.file_type;
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
    // Clean up blob URLs to prevent memory leaks
    if (this.currentDocumentUrl && this.currentDocumentUrl.startsWith('blob:')) {
      URL.revokeObjectURL(this.currentDocumentUrl);
    }
    
    this.documentViewerVisible = false;
    this.currentDocumentUrl = '';
    this.currentDocumentName = '';
    this.currentDocumentType = '';
  }

  performScroll(): void {
    let scrollContainer: HTMLElement | null = null;
    
    // Try ViewChild first
    if (this.scrollableContent && this.scrollableContent.nativeElement) {
      scrollContainer = this.scrollableContent.nativeElement;
    } else {
      // Fallback to querySelector
      scrollContainer = document.querySelector('.scrollable-content') as HTMLElement;
    }
    
    if (scrollContainer) {
      // Force immediate scroll to bottom
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
      
      // Then try smooth scroll
      setTimeout(() => {
        scrollContainer!.scrollTo({
          top: scrollContainer!.scrollHeight,
          behavior: 'smooth'
        });
      }, 50);
    }
  }

  scrollToProcessingResults(): void {
    // Legacy method - now just calls performScroll
    this.performScroll();
  }

  showToast(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    notify({
      message: message,
      type: type,
      displayTime: 4000,
      position: {
        my: 'top center',
        at: 'top center',
        offset: '0 80'
      }
    });
  }

  formatDate(date: string | Date): string {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleDateString('en-GB') + ' ' + d.toLocaleTimeString('en-GB', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  formatFileSize(bytes: number | string): string {
    if (!bytes) return 'Unknown size';
    if (typeof bytes === 'string') return bytes;
    
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  getFileIcon(fileType: string): string {
    return this.userDocumentsService.getFileIcon(fileType);
  }

  getFileTypeColor(fileType: string): string {
    return this.userDocumentsService.getFileTypeColor(fileType);
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

  // Bulk payslip uploader configuration
  bulkPayslipUploaderOptions = {
    multiple: true,
    accept: '.pdf',
    uploadMode: 'useButtons' as any,
    showFileList: true,
    labelText: 'Drop multiple payslip PDF files here or click to browse...',
    selectButtonText: 'Select Payslip PDFs',
    uploadButtonText: 'Process Payslips'
  };
}