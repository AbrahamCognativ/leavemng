import { Component, OnInit } from '@angular/core';
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
import { UserDocumentsService, UserDocument, UserDocumentCreate } from '../../../shared/services/user-documents.service';
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
export class UserDocumentsComponent implements OnInit {
  users: any[] = [];
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
    private userService: UserService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.loadCurrentUser();
    await this.loadUsers();
    await this.loadAllDocuments();
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

  onFileSelected(event: any): void {
    const files = event.value;
    if (files && files.length > 0) {
      this.selectedFile = files[0];
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
      const createData: UserDocumentCreate = {
        name: this.formData.title.trim(),
        description: this.formData.description?.trim() || undefined,
        user_id: this.formData.user_id,
        send_email_notification: true
      };
      
      await this.userDocumentsService.createUserDocument(createData, this.selectedFile);
      this.showToast('Document uploaded successfully', 'success');
      
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
    this.documentViewerVisible = false;
    this.currentDocumentUrl = '';
    this.currentDocumentName = '';
    this.currentDocumentType = '';
  }

  showToast(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    notify({
      message: message,
      type: type,
      displayTime: 4000,
      position: {
        my: 'top right',
        at: 'top right',
        offset: '20 20'
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
}