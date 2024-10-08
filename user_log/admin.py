from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account, Wallet, WalletHistory

class AccountAdmin(UserAdmin):
    list_display = ('email', 'username', 'date_joined', 'last_login', 'is_admin', 'is_staff')
    search_fields = ('email', 'username',)
    readonly_fields = ('date_joined', 'last_login')
    
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()



class UserWallet(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user',)

class UserWalletHistory(admin.ModelAdmin):
    list_display = ('wallet', 'type', 'created_at', 'amount')
    search_fields = ('wallet',)


admin.site.register(Account, AccountAdmin)
admin.site.register(Wallet, UserWallet)
admin.site.register(WalletHistory, UserWalletHistory)