import logging
from decimal import Decimal
from django.db import transaction

logger = logging.getLogger(__name__)

TRANSACTION_REFUND = 'Refund'
TRANSACTION_PAYMENT = 'Wallet Payment'


def get_or_create_wallet(user):
    from user_log.models import Wallet
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


def get_balance(user):
    wallet = get_or_create_wallet(user)
    return wallet.balance


def credit(user, amount, transaction_type=TRANSACTION_REFUND):
    from user_log.models import Wallet, WalletHistory
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError(f"Credit amount must be positive, got {amount}")

    # Ensure the row exists before we try to lock it.
    get_or_create_wallet(user)

    with transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)
        wallet.balance += amount
        wallet.save(update_fields=['balance'])
        WalletHistory.objects.create(wallet=wallet, type=transaction_type, amount=amount)
        logger.info("Credited ₹%s to wallet of user %s", amount, user.id)
    return wallet


def debit(user, amount, transaction_type=TRANSACTION_PAYMENT):
    from user_log.models import Wallet, WalletHistory
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError(f"Debit amount must be positive, got {amount}")

    get_or_create_wallet(user)

    with transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)
        if wallet.balance < amount:
            raise ValueError(
                f"Insufficient wallet balance. Available: {wallet.balance}, Required: {amount}"
            )
        wallet.balance -= amount
        wallet.save(update_fields=['balance'])
        WalletHistory.objects.create(wallet=wallet, type=transaction_type, amount=amount)
        logger.info("Debited ₹%s from wallet of user %s", amount, user.id)
    return wallet


def can_pay_with_wallet(user, amount):
    return get_balance(user) >= Decimal(str(amount))


def get_transaction_history(user):
    from user_log.models import WalletHistory
    wallet = get_or_create_wallet(user)
    return WalletHistory.objects.filter(wallet=wallet).order_by('-created_at')