import { Component, NgModule, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

import { DxListModule } from 'devextreme-angular/ui/list';
import { DxDropDownButtonModule } from 'devextreme-angular/ui/drop-down-button';
import { DxContextMenuModule } from 'devextreme-angular/ui/context-menu';
import {IUser} from '../../services';
import { UserStateService } from '../../services/user-state.service';

@Component({
  selector: 'app-user-panel',
  templateUrl: 'user-panel.component.html',
  styleUrls: ['./user-panel.component.scss'],
  standalone: false
})

export class UserPanelComponent {
  @Input()
  menuItems: any;

  @Input()
  menuMode = 'context';
  @Input() user!: IUser | null;

  constructor(private userStateService: UserStateService) {}

  get profileImageSrc(): string {
    return this.userStateService.getProfileImageSrc(this.user);
  }

  handleImageError(event: Event): void {
    const imgElement = event.target as HTMLImageElement;
    imgElement.src = this.userStateService.getProfileImageSrc();
  }
}

@NgModule({
  imports: [
    DxListModule,
    DxContextMenuModule,
    DxDropDownButtonModule,
    CommonModule
  ],
  declarations: [ UserPanelComponent ],
  exports: [ UserPanelComponent ],
  providers: [UserStateService]
})
export class UserPanelModule { }
