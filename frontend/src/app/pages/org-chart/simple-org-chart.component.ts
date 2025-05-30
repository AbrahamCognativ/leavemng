import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxButtonModule, DxLoadIndicatorModule } from 'devextreme-angular';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-simple-org-chart',
  standalone: true,
  imports: [CommonModule, DxButtonModule, DxLoadIndicatorModule],
  template: `
    <div class="org-chart-container">
      <h2 class="content-block">Organization Chart</h2>
      
      <div class="controls">
        <dx-button
          *ngIf="!initialized"
          text="Initialize Organization Structure"
          [disabled]="loading"
          (onClick)="initializeOrgStructure()"
          type="default">
        </dx-button>
        <dx-button
          *ngIf="initialized"
          text="Refresh Chart"
          [disabled]="loading"
          (onClick)="fetchOrgChartData()"
          type="default">
        </dx-button>
      </div>
      
      <div *ngIf="error" class="error-message">
        {{ error }}
      </div>
      
      <div *ngIf="loading" class="loading">
        <dx-load-indicator [visible]="true"></dx-load-indicator>
        <span>Loading organization chart...</span>
      </div>
      
      <div *ngIf="!loading && initialized" class="org-structure">
        <h3>Organization Structure</h3>
        
        <!-- Tree view representation of the org chart -->
        <div class="tree-container">
          <ng-container *ngTemplateOutlet="nodeTemplate; context:{nodes: orgData, level: 0}"></ng-container>
        </div>
      </div>
    </div>
    
    <!-- Recursive template for rendering org nodes -->
    <ng-template #nodeTemplate let-nodes="nodes" let-level="level">
      <div class="node-level" [class.level-{{level}}]="true">
        <div *ngFor="let node of nodes" class="org-node" [ngClass]="nodeClasses(node)">
          <div class="node-content">
            <div class="node-title">{{ node.type === 'unit' ? node.name : node.title }}</div>
            
            <div *ngIf="node.users && node.users.length > 0" class="node-users">
              <div *ngFor="let user of node.users" class="user-item">
                {{ user.name }}
              </div>
            </div>
          </div>
          
          <div *ngIf="node.children && node.children.length > 0" class="node-children">
            <ng-container *ngTemplateOutlet="nodeTemplate; context:{nodes: node.children, level: level + 1}"></ng-container>
          </div>
        </div>
      </div>
    </ng-template>
  `,
  styles: [`
    .org-chart-container {
      padding: 20px;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f9fafc;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    h2.content-block {
      color: #2c3e50;
      font-weight: 600;
      margin-bottom: 24px;
      border-bottom: 2px solid #3498db;
      padding-bottom: 12px;
      display: inline-block;
    }
    
    h3 {
      color: #34495e;
      font-weight: 500;
      margin-bottom: 16px;
    }
    
    .controls {
      margin-bottom: 24px;
      display: flex;
      gap: 12px;
    }
    
    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 40px 0;
      gap: 12px;
      color: #7f8c8d;
      font-size: 16px;
    }
    
    .error-message {
      background-color: #fff5f5;
      color: #e74c3c;
      padding: 16px;
      border-radius: 6px;
      margin: 16px 0;
      border-left: 4px solid #e74c3c;
      font-size: 14px;
    }
    
    .org-structure {
      margin-top: 30px;
      background-color: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .tree-container {
      margin-top: 20px;
      overflow-x: auto;
    }
    
    .node-level {
      display: flex;
      flex-wrap: wrap;
      gap: 20px;
      margin-bottom: 30px;
      position: relative;
    }
    
    .node-level:not(:last-child):after {
      content: '';
      position: absolute;
      bottom: -15px;
      left: 50%;
      width: 2px;
      height: 15px;
      background-color: #ddd;
    }
    
    .level-0 {
      justify-content: center;
    }
    
    .org-node {
      border-radius: 8px;
      overflow: hidden;
      min-width: 220px;
      box-shadow: 0 3px 10px rgba(0,0,0,0.08);
      transition: all 0.2s ease;
      border: 1px solid #eaeaea;
    }
    
    .org-node:hover {
      transform: translateY(-3px);
      box-shadow: 0 6px 15px rgba(0,0,0,0.1);
    }
    
    .org-node.unit {
      background-color: #e3f2fd;
      border-color: #bbdefb;
    }
    
    .org-node.role {
      background-color: #f5f5f5;
    }
    
    .org-node.manager {
      background: linear-gradient(135deg, #fff8e1 0%, #fffde7 100%);
      border-color: #ffecb3;
    }
    
    .node-content {
      padding: 16px;
    }
    
    .node-title {
      font-weight: 600;
      margin-bottom: 10px;
      color: #2c3e50;
      font-size: 15px;
      border-bottom: 1px solid rgba(0,0,0,0.1);
      padding-bottom: 8px;
    }
    
    .org-node.manager .node-title {
      color: #f39c12;
    }
    
    .node-users {
      font-size: 0.9em;
    }
    
    .user-item {
      padding: 6px 0;
      border-top: 1px dashed #eee;
      display: flex;
      align-items: center;
    }
    
    .user-item:before {
      content: '•';
      margin-right: 6px;
      color: #3498db;
    }
    
    .node-children {
      padding: 10px;
      padding-top: 0;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
      .node-level {
        flex-direction: column;
        align-items: center;
      }
      
      .org-node {
        width: 100%;
        max-width: 300px;
      }
    }
  `]
})
export class SimpleOrgChartComponent implements OnInit {
  orgData: any = null;
  loading = false;
  error: string | null = null;
  initialized = false;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    // Don't auto-load, wait for user to click initialize button
  }
  
  initializeOrgStructure(): void {
    // Set initialized first
    this.initialized = true;
    this.loading = true;
    
    // Load data from API
    this.fetchOrgChartData();
  }
  
  nodeClasses(node: any): any {
    return {
      'unit': node.type === 'unit',
      'role': node.type === 'role',
      'manager': node.is_manager
    };
  }

  // Fetch data from the API endpoint
  fetchOrgChartData(): void {
    this.loading = true;
    this.error = null;
    
    // Direct API call to the test-org-chart endpoint
    // const apiUrl = `${environment.apiBaseUrl}/test-org-chart`;
    const apiUrl = `${environment.apiBaseUrl}/api/v1/org/chart/tree`;
    console.log('Fetching organization chart from:', apiUrl);
    
    this.http.get(apiUrl).subscribe({
      next: (data: any) => {
        console.log('Successfully received org chart data:', data);
        this.orgData = data;
        this.loading = false;
      },
      error: (err: any) => {
        console.error('Error fetching org chart data:', err);
        this.error = `Failed to load organization chart. Error: ${err.message || 'Unknown error'}`;
        this.loading = false;
        
        // If API call fails, fall back to mock data
        if (confirm('Failed to load data from API. Load mock data instead?')) {
          this.loadMockData();
        }
      }
    });
  }
  
  loadMockData(): void {
    console.log('Loading mockup data for visualization');
    
    // Mockup data that matches the structure from the test-org-chart endpoint
    this.orgData = [
      {
        id: '00000000-0000-0000-0000-000000000001',
        title: 'Founder & CEO',
        type: 'role',
        is_manager: true,
        parent_id: null,
        users: [
          { id: 'user1', name: 'Ali Davachi' },
          { id: 'user2', name: 'Joel White' }
        ],
        children: [
          {
            id: '00000000-0000-0000-0000-000000000002',
            title: 'CTO Kenya',
            type: 'role',
            is_manager: true,
            parent_id: '00000000-0000-0000-0000-000000000001',
            users: [{ id: 'user3', name: 'Abraham Ogol' }],
            children: [
              {
                id: '00000000-0000-0000-0000-000000000005',
                title: 'Software Developer',
                type: 'role',
                is_manager: false,
                parent_id: '00000000-0000-0000-0000-000000000002',
                users: [
                  { id: 'user4', name: 'Mark Fenekayas' },
                  { id: 'user5', name: 'Claude Omosa' },
                  { id: 'user6', name: 'Stephen Kakwiri' },
                  { id: 'user7', name: 'Ivan Okello' },
                  { id: 'user8', name: 'Job Sidney' }
                ],
                children: []
              },
              {
                id: '00000000-0000-0000-0000-000000000006',
                title: 'QA Engineer',
                type: 'role',
                is_manager: false,
                parent_id: '00000000-0000-0000-0000-000000000002',
                users: [{ id: 'user9', name: 'Geryfell' }],
                children: []
              }
            ]
          },
          {
            id: '00000000-0000-0000-0000-000000000003',
            title: 'Director of Marketing',
            type: 'role',
            is_manager: true,
            parent_id: '00000000-0000-0000-0000-000000000001',
            users: [{ id: 'user10', name: 'Alina Davachi' }],
            children: [
              {
                id: '00000000-0000-0000-0000-000000000004',
                title: 'SEO Marketing Manager',
                type: 'role',
                is_manager: true,
                parent_id: '00000000-0000-0000-0000-000000000003',
                users: [{ id: 'user11', name: 'Kevin Anderson' }],
                children: []
              }
            ]
          },
          {
            id: '00000000-0000-0000-0000-000000000007',
            title: 'Director of Sales',
            type: 'role',
            is_manager: true,
            parent_id: '00000000-0000-0000-0000-000000000001',
            users: [{ id: 'user12', name: 'Scott Moss' }],
            children: [
              {
                id: '00000000-0000-0000-0000-000000000008',
                title: 'Business Development',
                type: 'role',
                is_manager: false,
                parent_id: '00000000-0000-0000-0000-000000000007',
                users: [
                  { id: 'user13', name: 'Monique Edgar' },
                  { id: 'user14', name: 'Sabrina Moreno' }
                ],
                children: []
              }
            ]
          }
        ]
      }
    ];
    
    this.loading = false;
  }
}
