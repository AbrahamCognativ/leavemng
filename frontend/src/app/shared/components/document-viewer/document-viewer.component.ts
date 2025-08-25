import { Component, Input, OnInit, OnDestroy, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxPopupModule, DxLoadPanelModule, DxButtonModule } from 'devextreme-angular';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { PolicyService } from '../../services/policy.service';

@Component({
  selector: 'app-document-viewer',
  standalone: true,
  imports: [CommonModule, DxPopupModule, DxLoadPanelModule, DxButtonModule],
  templateUrl: './document-viewer.component.html',
  styleUrls: ['./document-viewer.component.scss']
})
export class DocumentViewerComponent implements OnInit, OnDestroy, OnChanges {
  @Input() visible: boolean = false;
  @Input() documentUrl: string = '';
  @Input() documentName: string = '';
  @Input() fileType: string = '';

  safeUrl: SafeResourceUrl | null = null;
  isLoading: boolean = false;
  canPreview: boolean = false;
  errorMessage: string = '';
  documentKey: string = '';

  constructor(
    private sanitizer: DomSanitizer,
    private policyService: PolicyService
  ) {}

  ngOnInit() {
    this.updateDocumentUrl();
  }

  ngOnDestroy() {
    if (this.safeUrl) {
      this.safeUrl = null;
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['documentUrl'] || changes['visible'] || changes['fileType']) {
      this.updateDocumentUrl();
    }
  }

  private updateDocumentUrl() {
    if (this.documentUrl && this.visible) {
      this.isLoading = true;
      this.errorMessage = '';
      
      // Generate a unique key for this document to force iframe refresh
      this.documentKey = `${this.documentUrl}_${Date.now()}_${Math.random()}`;
      
      // Normalize file type to MIME type
      const normalizedFileType = this.normalizeFileType(this.fileType);
      
      // Determine if we can preview the document
      this.canPreview = this.canPreviewFileType(normalizedFileType);
      
      if (this.canPreview) {
        // Add cache-busting parameter to prevent browser caching
        const cacheBuster = `cacheBust=${Date.now()}`;
        const separator = this.documentUrl.includes('?') ? '&' : '?';
        const urlWithCacheBuster = `${this.documentUrl}${separator}${cacheBuster}`;
        
        // For PDFs, we can embed directly
        if (this.isPdf(normalizedFileType)) {
          this.safeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(urlWithCacheBuster);
        } else if (this.isDocx(normalizedFileType)) {
          // For DOCX files, use the preview endpoint that converts to PDF
          const previewUrl = this.getPreviewUrl(this.documentUrl);
          const previewUrlWithCacheBuster = `${previewUrl}${previewUrl.includes('?') ? '&' : '?'}${cacheBuster}`;
          this.safeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(previewUrlWithCacheBuster);
        } else {
          // For other files, we'll show a preview message
          this.safeUrl = null;
        }
      } else {
        this.safeUrl = null;
      }
      
      this.isLoading = false;
    } else if (!this.visible) {
      // Reset state when not visible
      this.resetState();
    }
  }

  onIframeError() {
    this.errorMessage = 'Unable to display document in browser. Please try downloading or opening in a new tab.';
    this.canPreview = false;
    this.safeUrl = null;
  }

  onIframeLoad() {
    this.isLoading = false;
    this.errorMessage = '';
  }

  normalizeFileType(fileType: string): string {
    const type = fileType.toLowerCase();
    
    // Convert file extensions to MIME types
    switch (type) {
      case 'pdf':
        return 'application/pdf';
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      case 'png':
        return 'image/png';
      case 'gif':
        return 'image/gif';
      case 'txt':
        return 'text/plain';
      case 'doc':
        return 'application/msword';
      case 'docx':
        return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
      case 'ppt':
        return 'application/vnd.ms-powerpoint';
      case 'pptx':
        return 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
      default:
        // If it's already a MIME type, return as is
        return type;
    }
  }

  private canPreviewFileType(fileType: string): boolean {
    const previewableTypes = [
      'application/pdf',
      'image/jpeg',
      'image/jpg',
      'image/png',
      'image/gif',
      'text/plain',
      // DOCX files can now be previewed via conversion
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword'
    ];
    return previewableTypes.includes(fileType.toLowerCase());
  }

  private resetState(): void {
    this.safeUrl = null;
    this.isLoading = false;
    this.canPreview = false;
    this.errorMessage = '';
    this.documentKey = '';
  }

  // Public methods for template access
  isPdf(fileType: string): boolean {
    const normalizedType = this.normalizeFileType(fileType);
    return normalizedType.toLowerCase() === 'application/pdf';
  }

  isImage(fileType: string): boolean {
    const normalizedType = this.normalizeFileType(fileType);
    return normalizedType.toLowerCase().startsWith('image/');
  }

  isDocx(fileType: string): boolean {
    const normalizedType = this.normalizeFileType(fileType);
    return normalizedType.toLowerCase() === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
           normalizedType.toLowerCase() === 'application/msword';
  }

  getPreviewUrl(originalUrl: string): string {
    // Extract policy ID from the original URL
    // Assuming URL format: /api/v1/policies/{id}/download?inline=true&token=...
    const urlParts = originalUrl.split('/');
    const policyIdIndex = urlParts.findIndex(part => part === 'policies') + 1;
    
    if (policyIdIndex > 0 && policyIdIndex < urlParts.length) {
      const policyId = urlParts[policyIdIndex];
      
      try {
        // Use PolicyService to get the proper preview URL with token
        return this.policyService.getPolicyPreviewUrl(policyId);
      } catch (error) {
        console.error('Error getting preview URL:', error);
        // Fallback to original URL if we can't get preview URL
        return originalUrl;
      }
    }
    
    // Fallback to original URL if we can't parse it
    return originalUrl;
  }

  onPopupHiding() {
    this.visible = false;
    this.resetState();
  }

}