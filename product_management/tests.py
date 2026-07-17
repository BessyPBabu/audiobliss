import io
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from user_log.models import Account
from product_management.models import Brand, Category, Color, Product, ProductVariant
from product_management.forms import ProductVariantForm
from product_management.admin import ProductAdmin
from django.contrib.admin.sites import AdminSite


def create_account(email, username, password='Pass1234!', is_admin=False):
    user = Account.objects.create_user(email=email, username=username, password=password)
    user.is_admin = is_admin
    user.save(update_fields=['is_admin'])
    return user


def make_image_file(content_type='image/png'):
    buf = io.BytesIO()
    Image.new('RGB', (10, 10)).save(buf, format='PNG')
    buf.seek(0)
    return SimpleUploadedFile('variant.png', buf.read(), content_type=content_type)


class ProductManagementAdminAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = create_account('padmin@example.com', 'padmin', is_admin=True)
        self.regular_user = create_account('puser@example.com', 'puser', is_admin=False)

    def test_anonymous_user_cannot_view_product_details(self):
        response = self.client.get(reverse('product_det:product_details'))
        self.assertEqual(response.status_code, 302)

    def test_regular_authenticated_user_cannot_add_product(self):
        self.client.login(email='puser@example.com', password='Pass1234!')
        response = self.client.get(reverse('product_det:add_product'))
        self.assertEqual(response.status_code, 302)

    def test_admin_user_can_view_product_details(self):
        self.client.login(email='padmin@example.com', password='Pass1234!')
        response = self.client.get(reverse('product_det:product_details'))
        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_delete_variant(self):
        self.client.login(email='puser@example.com', password='Pass1234!')
        response = self.client.post(reverse('product_det:add_variants'))
        self.assertEqual(response.status_code, 302)


class ProductVariantFormImageValidationTests(TestCase):
    def test_valid_image_passes(self):
        form = ProductVariantForm()
        form.cleaned_data = {'image1': make_image_file()}
        self.assertEqual(form.clean_image1(), form.cleaned_data['image1'])

    def test_non_image_bytes_rejected(self):
        fake = SimpleUploadedFile('fake.png', b'not-an-image', content_type='image/png')
        form = ProductVariantForm()
        form.cleaned_data = {'image1': fake}
        with self.assertRaises(Exception):
            form.clean_image1()

    def test_disallowed_content_type_rejected(self):
        bad = SimpleUploadedFile('script.svg', b'<svg onload="x()"></svg>', content_type='image/svg+xml')
        form = ProductVariantForm()
        form.cleaned_data = {'image1': bad}
        with self.assertRaises(Exception):
            form.clean_image1()

    def test_missing_image_field_returns_none(self):
        form = ProductVariantForm()
        form.cleaned_data = {'image1': None}
        self.assertIsNone(form.clean_image1())


class ProductAdminQuerysetFilterTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='AdminBrand')
        self.category = Category.objects.create(name='AdminCategory')
        self.active_product = Product.objects.create(
            title='Active Product', description='d', brand=self.brand, category=self.category, deleted=False
        )
        self.deleted_product = Product.objects.create(
            title='Deleted Product', description='d', brand=self.brand, category=self.category, deleted=True
        )
        self.admin_instance = ProductAdmin(Product, AdminSite())

    def test_soft_deleted_products_excluded_from_admin_queryset(self):
        from django.test import RequestFactory
        request = RequestFactory().get('/admin/product_management/product/')
        qs = self.admin_instance.get_queryset(request)
        self.assertIn(self.active_product, qs)
        self.assertNotIn(self.deleted_product, qs)