import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LeaveService } from '../../../shared/services/leave.service';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxPopupModule } from 'devextreme-angular/ui/popup';

@Component({
  selector: 'app-leave-types',
  templateUrl: './leave-types.component.html',
  styleUrls: ['./leave-types.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxDataGridModule,
    DxLoadIndicatorModule,
    DxFormModule,
    DxButtonModule,
    DxPopupModule
  ]
})
export class LeaveTypesComponent implements OnInit {
  leaveTypes: any[] = [];
  isLoading: boolean = false;
  isPopupVisible: boolean = false;
  currentLeaveType: any = {};

  constructor(private leaveService: LeaveService) { }

  ngOnInit(): void {
    this.loadLeaveTypes();
  }

  async loadLeaveTypes(): Promise<void> {
    try {
      this.isLoading = true;
      const types = await this.leaveService.getLeaveTypes();
      this.leaveTypes = types;
    } catch (error) {
      console.error('Error loading leave types:', error);
    } finally {
      this.isLoading = false;
    }
  }

  showAddPopup(): void {
    this.currentLeaveType = {};
    this.isPopupVisible = true;
  }

  showEditPopup(leaveType: any): void {
    this.currentLeaveType = { ...leaveType };
    this.isPopupVisible = true;
  }

  async saveLeaveType(): Promise<void> {
    try {
      if (this.currentLeaveType.id) {
        await this.leaveService.updateLeaveType(this.currentLeaveType.id, this.currentLeaveType);
      } else {
        await this.leaveService.createLeaveType(this.currentLeaveType);
      }
      this.isPopupVisible = false;
      await this.loadLeaveTypes();
    } catch (error) {
      console.error('Error saving leave type:', error);
    }
  }

  async deleteLeaveType(id: string): Promise<void> {
    try {
      await this.leaveService.deleteLeaveType(id);
      await this.loadLeaveTypes();
    } catch (error) {
      console.error('Error deleting leave type:', error);
    }
  }
} 