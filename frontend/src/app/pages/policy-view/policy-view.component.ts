import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxToastModule } from 'devextreme-angular/ui/toast';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { PdfViewerModule } from 'ng2-pdf-viewer';
import { PolicyService, Policy } from '../../shared/services/policy.service';
import { PolicyAcknowledmentService, UserPolicyStatus } from '../../shared/services/policy-acknowledgment.service';
import { AuthService } from '../../shared/services/auth.service';

interface PolicyContent {
  policy_id: string;
  policy_name: string;
  file_name: string;
  content: string;
  file_type: string;
}

@Component({
  selector: 'app-policy-view',
  templateUrl: './policy-view.component.html',
  styleUrls: ['./policy-view.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxButtonModule,
    DxToastModule,
    DxPopupModule,
    DxLoadIndicatorModule,
    PdfViewerModule
  ]
})
export class PolicyViewComponent implements OnInit, OnDestroy {
  policyId: string = '';
  policy: Policy | null = null;
  policyContent: PolicyContent | null = null;
  userPolicyStatus: UserPolicyStatus | null = null;
  currentUser: any = null;
  
  loading = false;
  contentLoading = false;
  toastVisible = false;
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' | 'warning' = 'info';
  
  // Electronic signing
  signaturePopupVisible = false;
  signing = false;
  
  // PDF viewer properties
  pdfSrc: string = '';
  pdfLoading = false;
  pdfError = false;
  showTextFallback = false;
  zoom = 0.75;
  totalPages = 0;
  private pdfBlobUrl: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private policyService: PolicyService,
    private policyAcknowledmentService: PolicyAcknowledmentService,
    private authService: AuthService
  ) {}

  async ngOnInit(): Promise<void> {
    this.route.params.subscribe(async params => {
      this.policyId = params['policyId'];
      if (this.policyId) {
        await this.loadData();
      }
    });
  }

  ngOnDestroy(): void {
    // Clean up blob URL to prevent memory leaks
    if (this.pdfBlobUrl) {
      URL.revokeObjectURL(this.pdfBlobUrl);
      this.pdfBlobUrl = null;
    }
  }

  async loadData(): Promise<void> {
    this.loading = true;
    
    // Reset all state variables when loading new policy
    this.resetPolicyState();
    
    try {
      await Promise.all([
        this.loadCurrentUser(),
        this.loadPolicy(),
        this.loadUserPolicyStatus()
      ]);
      
      if (this.policy) {
        await this.loadPolicyPdf();
      }
    } catch (error) {
      this.showToast('Error loading policy data', 'error');
    } finally {
      this.loading = false;
    }
  }

  private resetPolicyState(): void {
    // Reset PDF-related state
    this.pdfSrc = '';
    this.pdfLoading = false;
    this.pdfError = false;
    this.showTextFallback = false;
    this.zoom = 0.75;
    this.totalPages = 0;
    
    // Clean up previous blob URL
    if (this.pdfBlobUrl) {
      URL.revokeObjectURL(this.pdfBlobUrl);
      this.pdfBlobUrl = null;
    }
    
    // Reset content-related state
    this.policyContent = null;
    this.contentLoading = false;
    
    // Reset policy and user status (will be reloaded)
    this.policy = null;
    this.userPolicyStatus = null;
  }

  async loadCurrentUser(): Promise<void> {
    try {
      const userResult = await this.authService.getUser();
      if (userResult.isOk && userResult.data) {
        this.currentUser = userResult.data;
      }
    } catch (error) {
      console.error('Error loading current user:', error);
    }
  }

  async loadPolicy(): Promise<void> {
    try {
      this.policy = await this.policyService.getPolicy(this.policyId);
    } catch (error) {
      console.error('Error loading policy:', error);
      throw error;
    }
  }

  async loadUserPolicyStatus(): Promise<void> {
    try {
      const userPolicies = await this.policyAcknowledmentService.getUserPolicyStatus();
      this.userPolicyStatus = userPolicies.find(p => p.policy_id === this.policyId) || null;
    } catch (error) {
      console.error('Error loading user policy status:', error);
    }
  }

  async loadPolicyPdf(): Promise<void> {
    if (!this.policy) return;
    
    this.pdfLoading = true;
    this.pdfError = false;
    
    try {
      // For PDF files, load directly using preview endpoint
      if (this.policy.file_type.toLowerCase() === 'pdf') {
        // Reset text fallback state for PDF files
        this.showTextFallback = false;
        this.policyContent = null;
        
        // Use the preview endpoint which handles authentication properly
        this.pdfSrc = await this.getPdfUrl();
      } else {
        // For other files, reset PDF state and load text content
        this.pdfSrc = '';
        if (this.pdfBlobUrl) {
          URL.revokeObjectURL(this.pdfBlobUrl);
          this.pdfBlobUrl = null;
        }
        
        // Load text content for non-PDF files
        await this.loadPolicyContent();
        this.showTextFallback = true;
      }
    } catch (error) {
      console.error('Error loading policy PDF:', error);
      this.pdfError = true;
      // Fall back to text content
      await this.loadPolicyContent();
      this.showTextFallback = true;
    } finally {
      this.pdfLoading = false;
    }
  }

  private async getPdfUrl(): Promise<string> {
    // Clean up previous blob URL if exists
    if (this.pdfBlobUrl) {
      URL.revokeObjectURL(this.pdfBlobUrl);
      this.pdfBlobUrl = null;
    }
    
    // Create a blob URL for the PDF to handle authentication
    try {
      const token = localStorage.getItem('user_token');
      const response = await fetch(`${this.policyService['API_URL']}/policies/${this.policyId}/download?inline=true&token=${encodeURIComponent(token || '')}`, {
        // No Authorization header needed since we're using token parameter
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load PDF: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      this.pdfBlobUrl = URL.createObjectURL(blob);
      return this.pdfBlobUrl;
    } catch (error) {
      console.error('Error creating PDF URL:', error);
      throw error;
    }
  }

  async loadPolicyContent(): Promise<void> {
    if (!this.policy) return;
    
    this.contentLoading = true;
    try {
      const token = localStorage.getItem('user_token');
      const response = await fetch(`${this.policyService['API_URL']}/policies/${this.policyId}/content?token=${encodeURIComponent(token || '')}`, {
        // No Authorization header needed since we're using token parameter
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load policy content: ${response.statusText}`);
      }
      
      this.policyContent = await response.json();
    } catch (error) {
      console.error('Error loading policy content:', error);
      this.showToast('Error loading policy content. You can still download the file.', 'warning');
    } finally {
      this.contentLoading = false;
    }
  }

  // PDF viewer event handlers
  onPdfLoadComplete(pdf: any): void {
    this.totalPages = pdf.numPages;
    this.pdfError = false;
  }

  onPdfError(error: any): void {
    console.error('PDF loading error:', error);
    this.pdfError = true;
    this.showTextFallback = true;
    // Try to load text content as fallback
    this.loadPolicyContent();
  }

  // PDF viewer controls
  zoomIn(): void {
    this.zoom = Math.min(this.zoom + 0.25, 3.0);
  }

  zoomOut(): void {
    this.zoom = Math.max(this.zoom - 0.25, 0.5);
  }

  resetZoom(): void {
    this.zoom = 0.75;
  }

  showToast(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    this.toastMessage = message;
    this.toastType = type;
    this.toastVisible = true;
  }

  async downloadPolicy(): Promise<void> {
    if (!this.policy) return;
    
    try {
      await this.policyService.downloadPolicy(this.policy.id, this.policy.file_name);
      this.showToast(`Downloaded ${this.policy.file_name}`, 'success');
    } catch (error: any) {
      let errorMessage = 'Error downloading policy';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
  }

  openSignaturePopup(): void {
    this.signaturePopupVisible = true;
  }

  closeSignaturePopup(): void {
    this.signaturePopupVisible = false;
  }

  async acknowledgePolicy(): Promise<void> {
    if (!this.policy || !this.currentUser) {
      return;
    }

    this.signing = true;
    try {
      await this.policyAcknowledmentService.acknowledgePolicy({
        policy_id: this.policy.id,
        user_id: this.currentUser.id,
        signature_method: 'electronic_signature'
      });

      this.showToast('Policy acknowledged successfully! A signed copy will be sent to your email.', 'success');
      this.closeSignaturePopup();
      
      // Refresh user policy status
      await this.loadUserPolicyStatus();
      
      // Navigate back to dashboard or policies
      setTimeout(() => {
        this.router.navigate(['/dashboard']);
      }, 2000);
      
    } catch (error: any) {
      let errorMessage = 'Error acknowledging policy';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    } finally {
      this.signing = false;
    }
  }

  canAcknowledge(): boolean {
    return this.userPolicyStatus ? !this.userPolicyStatus.is_acknowledged : false;
  }

  getStatusColor(): string {
    if (!this.userPolicyStatus) return '#6c757d';
    return this.policyAcknowledmentService.getStatusColor(this.userPolicyStatus);
  }

  getStatusText(): string {
    if (!this.userPolicyStatus) return 'Unknown';
    return this.policyAcknowledmentService.getStatusText(this.userPolicyStatus);
  }

  getStatusIcon(): string {
    if (!this.userPolicyStatus) return 'dx-icon-help';
    return this.policyAcknowledmentService.getStatusIcon(this.userPolicyStatus);
  }

  getDaysRemainingText(): string {
    if (!this.userPolicyStatus) return '';
    
    if (this.userPolicyStatus.is_acknowledged) return 'Completed';
    if (this.userPolicyStatus.is_overdue) return 'Overdue';
    if (this.userPolicyStatus.days_remaining !== null && this.userPolicyStatus.days_remaining !== undefined) {
      return `${this.userPolicyStatus.days_remaining} days left`;
    }
    return 'No deadline';
  }

  formatDate(date: string | Date): string {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleDateString('en-GB') + ' ' + d.toLocaleTimeString('en-GB', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }

  // Format content for better display
  formatContent(content: string): string {
    if (!content) return '';
    
    // Enhanced formatting to preserve document structure
    return content
      .replace(/\r\n/g, '\n') // Normalize line endings
      .replace(/\n\s*\n\s*\n/g, '\n\n') // Normalize multiple line breaks to double
      .replace(/^\s+|\s+$/g, '') // Trim whitespace
      .replace(/\t/g, '    ') // Convert tabs to spaces
      .trim();
  }

  // Split content into structured sections for better rendering
  getContentParagraphs(): any[] {
    if (!this.policyContent?.content) return [];
    
    const formatted = this.formatContent(this.policyContent.content);
    const paragraphs = formatted.split(/\n\s*\n/); // Split on double line breaks
    const sections: any[] = [];
    
    for (const paragraph of paragraphs) {
      const trimmed = paragraph.trim();
      if (!trimmed) continue;
      
      const lines = trimmed.split('\n');
      const firstLine = lines[0].trim();
      
      // Check if first line is a heading
      if (this.isHeading(firstLine, lines, 0)) {
        // Add heading
        sections.push({
          type: 'heading',
          content: firstLine,
          level: this.getHeadingLevel(firstLine)
        });
        
        // Add remaining content as paragraph if exists
        const remainingContent = lines.slice(1).join('\n').trim();
        if (remainingContent) {
          sections.push({
            type: 'paragraph',
            content: remainingContent
          });
        }
      } else {
        // Regular paragraph
        sections.push({
          type: 'paragraph',
          content: trimmed
        });
      }
    }
    
    return sections;
  }
  
  private isHeading(line: string, lines: string[], index: number): boolean {
    // Check if line looks like a heading
    const nextLine = index + 1 < lines.length ? lines[index + 1].trim() : '';
    const isShort = line.length < 80;
    const isAllCaps = line === line.toUpperCase() && line.length > 3;
    const hasNumbers = /^\d+\./.test(line); // Starts with number
    const isFollowedByContent = Boolean(nextLine && nextLine.length > 0);
    const endsWithColon = line.endsWith(':');
    
    return (isShort && (isAllCaps || hasNumbers || endsWithColon)) ||
           (isShort && isFollowedByContent && line.length < 50);
  }
  
  private getHeadingLevel(line: string): number {
    if (/^\d+\./.test(line)) return 2; // Numbered headings
    if (line === line.toUpperCase()) return 1; // All caps
    if (line.endsWith(':')) return 3; // Colon endings
    return 2; // Default
  }

  getCurrentDateString(): string {
    return this.formatDate(new Date());
  }

  formatParagraphText(text: string): string {
    if (!text) return '';
    
    // Convert line breaks to HTML and preserve formatting
    return text
      .replace(/\n\n/g, '</p><p>') // Convert double line breaks to paragraphs
      .replace(/\n/g, '<br>') // Convert single line breaks to <br>
      .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;') // Convert tabs
      .replace(/  /g, '&nbsp;&nbsp;') // Preserve double spaces
      .replace(/^/, '<p>') // Add opening paragraph tag
      .replace(/$/, '</p>'); // Add closing paragraph tag
  }
}