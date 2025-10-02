# Stripe Integration Documentation

## Overview
Complete Stripe payment integration for VAT Verification SaaS platform with subscription management, checkout flow, and webhook processing.

---

## Features Implemented

### 1. Subscription Plans & Pricing
**File:** `payments/routes.py`, `templates/payments/pricing.html`

Three-tier pricing model:
- **Free Plan**: €0/month, 5 checks/month
- **Pro Plan**: €49/month, 500 checks/month
- **Enterprise Plan**: €149/month, unlimited checks

**Key Routes:**
- `GET /payments/pricing` - Display pricing page with plan comparison
- `GET /payments/subscribe/<plan_name>` - Create Stripe Checkout session
- `GET /payments/success` - Handle successful payment
- `GET /payments/cancel` - Handle cancelled payment
- `GET /payments/customer_portal` - Redirect to Stripe Customer Portal

### 2. Stripe Checkout Integration
**Implementation:** `payments/routes.py::subscribe()`

Creates Stripe Checkout session with:
```python
stripe.checkout.Session.create(
    payment_method_types=['card'],
    mode='subscription',
    line_items=[...],
    success_url=url_for('payments.success'),
    cancel_url=url_for('payments.cancel'),
    metadata={'user_id': ..., 'plan_name': ...}
)
```

**Features:**
- Automatic currency conversion (EUR)
- Customer email pre-filled
- User ID and plan name stored in metadata
- Secure redirect to Stripe-hosted checkout page

### 3. Payment Success Handling
**Implementation:** `payments/routes.py::success()`

Post-payment processing:
1. Retrieve Stripe session with `session_id` from query params
2. Verify user matches session metadata
3. Update/create Subscription record:
   - Set `stripe_subscription_id` and `stripe_customer_id`
   - Update `plan`, `status` (active), `api_calls_limit`
   - Reset `api_calls_used` to 0
   - Set billing period dates (30 days)
4. Redirect to dashboard with success message

### 4. Stripe Customer Portal
**Implementation:** `payments/routes.py::customer_portal()`

Redirects users to Stripe-hosted portal for:
- Update payment method
- Cancel subscription
- View/download invoices
- Update billing information

```python
stripe.billing_portal.Session.create(
    customer=subscription.stripe_customer_id,
    return_url=url_for('auth.profile')
)
```

### 5. Webhook Event Processing
**File:** `payments/webhooks.py`

**Endpoint:** `POST /webhooks/stripe`

Handles Stripe webhook events with signature verification:

#### Events Handled:

##### `checkout.session.completed`
- Triggered when user completes Stripe Checkout
- Updates subscription with Stripe IDs
- Activates subscription
- Resets API quota

##### `customer.subscription.created`
- Confirms subscription activation
- Updates billing period dates
- Sets status to 'active'

##### `customer.subscription.updated`
- Handles plan changes (upgrade/downgrade)
- Updates subscription status
- Refreshes billing period dates

##### `customer.subscription.deleted`
- Triggered when subscription cancelled
- Downgrades user to Free plan (5 checks/month)
- Sets status to 'cancelled'
- Clears Stripe subscription ID

##### `invoice.payment_succeeded`
- Monthly recurring payment successful
- Creates Payment record in database
- Resets monthly API usage counter
- Updates billing period

##### `invoice.payment_failed`
- Payment declined/failed
- Sets subscription status to 'past_due'
- Creates failed Payment record
- Triggers email notification (TODO)

**Security:** HMAC signature verification with `STRIPE_WEBHOOK_SECRET`

### 6. UI Integration

#### Navigation Updates (`templates/base.html`)
- Added "Abonnement" link to user dropdown → `/payments/pricing`
- Added "Zahlungen verwalten" link → `/payments/customer_portal`
- Updated guest navigation "Preise" → `/payments/pricing`

#### Profile Page Enhancement (`templates/auth/profile.html`)
- Display current plan with badge (Free/Pro/Enterprise)
- Show API usage: `X / Y diesen Monat`
- "Upgrade" button for free users → `/payments/pricing`
- "Verwalten" button for paid users → `/payments/customer_portal`

#### Success/Cancel Pages
- `templates/payments/success.html` - Confirmation page with subscription details
- `templates/payments/cancel.html` - Reassurance message, links to retry or return

---

## Configuration Required

### Environment Variables (`.env`)

```bash
# Stripe API Keys (get from https://dashboard.stripe.com/apikeys)
STRIPE_PUBLIC_KEY=pk_test_51XXXXXXXXXXXXX  # Test: pk_test_, Live: pk_live_
STRIPE_SECRET_KEY=sk_test_51XXXXXXXXXXXXX  # Test: sk_test_, Live: sk_live_

# Webhook Secret (from Stripe Dashboard → Webhooks)
STRIPE_WEBHOOK_SECRET=whsec_XXXXXXXXXXXXXXX
```

### Stripe Dashboard Setup

1. **Create Products:**
   - Professional Plan: €49.00/month
   - Enterprise Plan: €149.00/month

2. **Configure Webhook Endpoint:**
   - URL: `https://yourdomain.com/webhooks/stripe`
   - Events to send:
     - `checkout.session.completed`
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`

3. **Enable Customer Portal:**
   - Navigate to Settings → Billing → Customer Portal
   - Enable portal
   - Configure allowed actions: update payment method, cancel subscription

---

## Database Schema

### Subscription Model Updates
```python
class Subscription(db.Model):
    stripe_subscription_id = db.Column(db.String(255))  # sub_XXXXX
    stripe_customer_id = db.Column(db.String(255))      # cus_XXXXX
    status = db.Column(db.String(50))  # active, cancelled, past_due
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
```

### Payment Model
```python
class Payment(db.Model):
    user_id = db.Column(db.Integer, ForeignKey)
    subscription_id = db.Column(db.Integer, ForeignKey)
    stripe_payment_intent_id = db.Column(db.String(255))  # pi_XXXXX
    amount = db.Column(db.Float)  # Amount in EUR
    currency = db.Column(db.String(3))  # EUR
    status = db.Column(db.String(50))  # succeeded, failed
    created_at = db.Column(db.DateTime)
```

---

## Testing Workflow

### 1. Test Checkout Flow
```bash
# Use Stripe test card numbers
4242 4242 4242 4242  # Successful payment
4000 0000 0000 9995  # Declined payment
```

**Test Steps:**
1. Register new user (free plan)
2. Go to `/payments/pricing`
3. Click "Upgrade auf Pro"
4. Complete Stripe Checkout with test card
5. Verify redirect to success page
6. Check subscription updated in database
7. Verify API limit increased to 500

### 2. Test Webhook Processing
```bash
# Install Stripe CLI
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:5000/webhooks/stripe

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger invoice.payment_succeeded
stripe trigger customer.subscription.deleted
```

### 3. Test Customer Portal
1. Login as user with paid subscription
2. Navigate to Profile → "Verwalten" button
3. Verify redirect to Stripe Customer Portal
4. Test cancellation flow
5. Verify webhook downgrade to free plan

---

## Security Considerations

1. **Webhook Signature Verification**
   - All webhook requests verified with HMAC signature
   - Prevents unauthorized webhook spoofing

2. **User ID Verification**
   - Success callback checks `current_user.id` matches session metadata
   - Prevents subscription hijacking

3. **API Key Security**
   - Keys stored in environment variables (never committed to git)
   - Use test keys in development, live keys in production

4. **HTTPS Required**
   - Stripe webhooks require HTTPS in production
   - Use ngrok/Stripe CLI for local testing

---

## Error Handling

### Stripe API Errors
```python
try:
    checkout_session = stripe.checkout.Session.create(...)
except stripe.error.StripeError as e:
    flash('Fehler beim Erstellen der Checkout-Sitzung.', 'danger')
    logger.error(f"Stripe error: {str(e)}")
```

### Webhook Failures
- All handlers wrapped in try/except
- Errors logged with `current_app.logger`
- Returns 200 OK even on error (prevents Stripe retries)

---

## Future Enhancements

### TODO List:
1. **Email Notifications:**
   - Send confirmation email after successful payment
   - Send cancellation confirmation
   - Send payment failure notifications

2. **Invoice Generation:**
   - Create PDF invoices for each payment
   - Store in S3/Cloud Storage
   - Add download link in Customer Portal

3. **Proration Handling:**
   - Calculate prorated amounts for mid-cycle upgrades
   - Credit remaining balance on downgrades

4. **Multi-Currency Support:**
   - Add USD, GBP pricing
   - Stripe automatic currency conversion

5. **Annual Billing:**
   - Add annual plan options with discount
   - Update webhook handlers for yearly cycles

6. **Usage-Based Billing:**
   - Charge per additional API call over limit
   - Implement metered billing with Stripe

---

## Troubleshooting

### Issue: Webhooks not received
**Solution:**
- Check webhook endpoint URL in Stripe Dashboard
- Verify `STRIPE_WEBHOOK_SECRET` matches dashboard
- Check server logs for incoming requests
- Use Stripe CLI to test locally

### Issue: Payment succeeded but subscription not updated
**Solution:**
- Check webhook handler logs
- Verify user_id in session metadata
- Check database for Subscription record
- Review `checkout.session.completed` handler

### Issue: Customer Portal shows 404
**Solution:**
- Verify Customer Portal enabled in Stripe Dashboard
- Check `stripe_customer_id` exists in subscription
- Ensure user has active paid subscription

---

## Deployment Checklist

- [ ] Replace test API keys with live keys
- [ ] Update webhook endpoint to production URL
- [ ] Enable HTTPS on production server
- [ ] Test live payment with real card (refund after)
- [ ] Monitor webhook delivery in Stripe Dashboard
- [ ] Set up error alerting (Sentry/Rollbar)
- [ ] Create backup webhook endpoint
- [ ] Document runbook for payment failures

---

## Status: ✅ COMPLETE

**Completed:**
- Stripe Checkout integration
- Subscription management
- Webhook event processing
- Customer Portal redirect
- UI integration (navigation, profile, pricing)
- Success/cancel pages
- Documentation

**Next Steps:**
- Task #6: Admin Dashboard
- Task #7: User Dashboard Enhancement
- Email notifications for payments
