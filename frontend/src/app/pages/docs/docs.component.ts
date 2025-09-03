import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxSelectBoxModule } from 'devextreme-angular/ui/select-box';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxiItemModule, DxoLabelModule, DxiColumnModule, DxoPagingModule, DxoPagerModule, DxoSearchPanelModule, DxoHeaderFilterModule, DxoFilterRowModule, DxoExportModule } from 'devextreme-angular/ui/nested';
import { RouterModule, Router } from '@angular/router';
import { UserDocumentsService, MyDocument } from '../../shared/services/user-documents.service';
import { AuthService } from '../../shared/services/auth.service';
import { DocumentViewerComponent } from '../../shared/components/document-viewer/document-viewer.component';
import notify from 'devextreme/ui/notify';

@Component({
  selector: 'app-docs',
  templateUrl: './docs.component.html',
  styleUrls: ['./docs.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxDataGridModule,
    DxButtonModule,
    DxSelectBoxModule,
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
    RouterModule,
    DocumentViewerComponent
  ]
})
export class DocsComponent implements OnInit {
  documents: MyDocument[] = [];
  loading = false;
  
  selectedDocumentType: string | null = null;
  documentTypes = [
    { id: null, name: 'All Document Types' },
    { id: 'contract', name: 'Contracts' },
    { id: 'certificate', name: 'Certificates' },
    { id: 'handbook', name: 'Handbooks' },
    { id: 'policy', name: 'Policies' },
    { id: 'other', name: 'Other' }
  ];
  
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
    private router: Router
  ) {}

  async ngOnInit(): Promise<void> {
    await this.loadCurrentUser();
    await this.loadDocuments();
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

  async loadDocuments(): Promise<void> {
    this.loading = true;
    try {
      this.documents = await this.userDocumentsService.getMyDocuments();
    } catch (error) {
      this.showToast('Error loading documents', 'error');
    } finally {
      this.loading = false;
    }
  }

  async onDocumentTypeFilterChanged(event: any): Promise<void> {
    this.selectedDocumentType = event.value;
    // Filter documents locally since the API returns all user documents
    // In a real implementation, you might want to add filtering to the API
  }

  get filteredDocuments(): MyDocument[] {
    if (!this.selectedDocumentType) {
      return this.documents;
    }
    return this.documents.filter(doc => 
      (doc.document_type || 'other') === this.selectedDocumentType
    );
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

  async downloadDocument(document: MyDocument): Promise<void> {
    try {
      await this.userDocumentsService.downloadDocument(document.id, document.file_name);
      this.showToast(`Downloaded ${document.file_name}`, 'success');
    } catch (error: any) {
      let errorMessage = 'Error downloading document';
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
    return this.userDocumentsService.getFileIcon(fileType);
  }

  getFileTypeColor(fileType: string): string {
    return this.userDocumentsService.getFileTypeColor(fileType);
  }

  getDocumentTypeIcon(documentType?: string): string {
    return this.userDocumentsService.getDocumentTypeIcon(documentType);
  }

  getDocumentTypeColor(documentType?: string): string {
    return this.userDocumentsService.getDocumentTypeColor(documentType);
  }

  getDocumentTypeDisplayName(documentType?: string): string {
    const type = this.documentTypes.find(t => t.id === documentType);
    return type ? type.name : 'Other';
  }

  canManageDocuments(): boolean {
    return this.isAdmin || this.isHR || this.isManager;
  }

  navigateToManageDocuments(): void {
    this.router.navigate(['/admin/user-documents']);
  }

  viewDocument(document: MyDocument): void {
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

  onRowClick(event: any): void {
    // Get the document data from the clicked row
    const document = event.data;
    if (document) {
      this.viewDocument(document);
    }
  }

  closeDocumentViewer(): void {
    this.documentViewerVisible = false;
    this.currentDocumentUrl = '';
    this.currentDocumentName = '';
    this.currentDocumentType = '';
  }
}