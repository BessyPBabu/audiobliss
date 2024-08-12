from django.urls import path
from product_management import views

app_name = 'product_det'


urlpatterns = [
   
    path('product_details/',views.product_details,name='product_details'),
    path('add_product/',views.add_product,name='add_product'),
    path('product/update/<int:pk>/', views.product_update, name='product_update'),
    path('product/delete/<int:pk>/', views.product_delete, name='product_delete'),
   
    path('add_variants/', views.add_variants, name='add_variants'),
    path('variant_details/', views.variant_details, name='variant_details'),
    path('edit_variant/<int:variant_id>/', views.edit_variant, name='edit_variant'),
    path('delete_variant/<int:variant_id>/', views.delete_variant, name='delete_variant'),

    path('categories/', views.category_list, name='categories'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/update/<int:pk>/', views.category_update, name='category_update'),
    path('categories/delete/<int:pk>/', views.category_delete, name='category_delete'),

  

]