import {Component, OnInit} from '@angular/core';
import {DxFormModule} from 'devextreme-angular/ui/form';

@Component({
  templateUrl: 'profile.component.html',
  styleUrls: [ './profile.component.scss' ],
  standalone: true,
  imports: [DxFormModule]
})

export class ProfileComponent implements OnInit{
  employee: any;
  colCountByScreen: object;
  constructor() {
    this.colCountByScreen = {
      xs: 1,
      sm: 2,
      md: 3,
      lg: 4
    };
  }

  async ngOnInit(): Promise<void> {
    try {
      const rawUser = localStorage.getItem("current_user");
      const parsedUser = rawUser ? JSON.parse(rawUser) : null;

      if (parsedUser) {
        this.employee = {
          id: parsedUser.id,
          name: parsedUser.name,
          email: parsedUser.email,
          passport_or_id_number: parsedUser.passport_or_id_number,
          manager_id: parsedUser.manager_id,
          role_band: parsedUser.role_band,
        };

      }
    } catch (err) {
      console.error('Failed to load user data:', err);
    }
  }

}
