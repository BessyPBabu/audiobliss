from django.urls import path
from . import views

app_name = 'offer_management'


urlpatterns = [
    path('', views.offer_list, name='offer_list'),
    path('<int:pk>/', views.offer_detail, name='offer_detail'),
    path('create/', views.offer_create, name='offer_create'),
    path('<int:pk>/update/', views.offer_update, name='offer_update'),
    path('<int:pk>/delete/', views.offer_delete, name='offer_delete'),
    path('product-offer/create/', views.product_offer_create, name='product_offer_create'),
    path('category-offer/create/', views.category_offer_create, name='category_offer_create'),
    # path('referral-offer/create/', views.referral_offer_create, name='referral_offer_create'),
]