import { Component, EventEmitter, Input, OnInit, Output, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxFileUploaderModule } from 'devextreme-angular/ui/file-uploader';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxTextAreaModule } from 'devextreme-angular/ui/text-area';
import { DxiItemModule, DxoLabelModule } from 'devextreme-angular/ui/nested';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { BytesPipe } from '../../../pipes/bytes.pipe';
import { LeaveService } from '../../../shared/services/leave.service';

@Component({
  selector: 'app-edit-leave-modal',
  templateUrl: './edit-leave-modal.component.html',
  styleUrls: ['./edit-leave-modal.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxFormModule,
    DxButtonModule,
    DxiItemModule,
    DxoLabelModule,
    DxFileUploaderModule,
    DxLoadIndicatorModule,
    DxTextAreaModule,
    DxPopupModule,
    BytesPipe
  ],
})
export class EditLeaveModalComponent implements OnInit, OnChanges {
  @Input() visible: boolean = false;
  @Input() leaveRequest: any = null;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() onLeaveUpdated = new EventEmitter<any>();
  
  // Define the auto property for the height
  auto: string = 'auto';

  editData: any = {
    comments: '',
    documents: []
  };
  uploadedFiles: File[] = [];
  submitting = false;
  existingDocuments: any[] = [];

  constructor(private leaveService: LeaveService) {}

  ngOnInit(): void {}

  ngOnChanges(): void {
    if (this.leaveRequest) {
      this.editData.comments = this.leaveRequest.comments || '';
      this.loadExistingDocuments();
    }
  }

  async loadExistingDocuments(): Promise<void> {
    if (!this.leaveRequest || !this.leaveRequest.id) return;

    try {
      // Get existing documents for this leave request
      const leaveDetails = await this.leaveService.getLeaveRequestDetails(this.leaveRequest.id);
      if (leaveDetails && leaveDetails.documents) {
        this.existingDocuments = leaveDetails.documents.map((doc: any) => ({
          id: doc.id,
          name: doc.filename || doc.name,
          fileType: doc.content_type || doc.fileType,
          size: doc.size || 0,
          uploadDate: new Date(doc.created_at || doc.uploadDate)
        }));
      }
    } catch (error) {
      console.error('Error loading existing documents:', error);
    }
  }

  onFileUploaded(e: any): void {
    if (e.value && e.value.length > 0) {
      this.uploadedFiles = e.value;
    }
  }

  removeDocument(id: string): void {
    if (this.leaveRequest && this.leaveRequest.id) {
      this.leaveService.deleteLeaveDocument(this.leaveRequest.id, id)
        .then(() => {
          this.existingDocuments = this.existingDocuments.filter(doc => doc.id !== id);
        })
        .catch(error => {
          console.error('Error deleting document:', error);
        });
    }
  }

  async saveChanges(): Promise<void> {
    if (this.submitting) return;
    this.submitting = true;

    try {
      // 1. Update leave request comments
      const updateData = {
        comments: this.editData.comments
      };

      await this.leaveService.updateLeaveRequest(this.leaveRequest.id, updateData);

      // 2. Upload any new files
      if (this.uploadedFiles.length > 0) {
        for (const file of this.uploadedFiles) {
          await this.leaveService.uploadFile(this.leaveRequest.id, file);
        }
      }

      // 3. Emit success event
      this.onLeaveUpdated.emit({
        success: true,
        leaveId: this.leaveRequest.id
      });

      // 4. Close modal
      this.closeModal();
    } catch (error) {
      console.error('Error updating leave request:', error);
    } finally {
      this.submitting = false;
    }
  }

  closeModal(): void {
    this.visible = false;
    this.visibleChange.emit(false);
    this.uploadedFiles = [];
    this.editData = {
      comments: '',
      documents: []
    };
  }
}
