import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OrgUnitService } from '../../shared/services/org-unit.service';
import { OrgNode } from '../../models/org.model';
import { DxLoadIndicatorModule, DxButtonModule, DxSwitchModule } from 'devextreme-angular';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-org-chart',
  templateUrl: './org-chart.component.html',
  styleUrls: ['./org-chart.component.scss'],
  standalone: true,
  imports: [CommonModule, DxLoadIndicatorModule, DxButtonModule, DxSwitchModule]
})
export class OrgChartComponent implements OnInit {
  orgData: any;
  loading = true;
  error: string | null = null;
  isTestData = false;
  dataSource = 'Database';
  
  // Helper method for template to check if data is an array
  isArray(data: any): boolean {
    return Array.isArray(data);
  }

  constructor(private orgUnitService: OrgUnitService, private http: HttpClient) { }

  ngOnInit(): void {
    this.loadOrgChart();
  }
  
  toggleDataSource(): void {
    this.isTestData = !this.isTestData;
    this.dataSource = this.isTestData ? 'Test Data' : 'Database';
    this.loading = true;
    this.error = null;
    
    if (this.isTestData) {
      this.loadTestData();
    } else {
      this.loadOrgChart();
    }
  }

  loadOrgChart(): void {
    this.loading = true;
    this.error = null;
    
    // Use the real API endpoint to get your actual organization data
    this.orgUnitService.getOrgChart().subscribe({
      next: (data) => {
        console.log('Real org chart data received:', data);
        this.orgData = data;
        this.loading = false;
        
        // If no data was received, show a helpful message
        if (!data || (Array.isArray(data) && data.length === 0)) {
          this.error = 'No organizational data found in the database. Please create organization units first.';
        }
      },
      error: (err) => {
        console.error('Error loading real org chart data:', err);
        this.error = 'Failed to load organizational chart';
        this.loading = false;
        
        // We won't use the fake test data anymore
        // this.loadTestData();
      }
    });
  }
  
  loadTestData(): void {
    console.log('Loading test org chart data');
    
    // Use the test data endpoint directly with minimal error handling
    this.http.get(`${environment.apiUrl}/org/chart-test`).subscribe({
      next: (data: any) => {
        console.log('Test org chart data received:', data);
        this.orgData = data;
        this.loading = false;
        this.error = null;
      },
      error: (err: any) => {
        console.error('Error loading test data:', err);
        this.error = 'Failed to load test data. Check console for details.';
        this.loading = false;
      }
    });
  }

  getNodeStyle(node: OrgNode): any {
    if (node.type === 'unit') {
      return { backgroundColor: '#3498db', color: 'white' };
    } else if (node.is_manager) {
      return { backgroundColor: '#e74c3c', color: 'white' };
    } else {
      return { backgroundColor: '#2ecc71', color: 'white' };
    }
  }

  getNodeDetails(node: OrgNode): string {
    if (node.type === 'unit') {
      return `Department: ${node.name}`;
    } else {
      let details = `Role: ${node.title}`;
      if (node.users && node.users.length > 0) {
        details += `
Staff: ${node.users.map(u => u.name).join(', ')}`;
      }
      return details;
    }
  }
}

