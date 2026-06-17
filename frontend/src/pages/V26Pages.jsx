/* V26 admin pages — barrel re-export.
 * Individual page implementations live in /pages/v26/.
 */
import Barcode128 from '../components/Barcode128';
import VoucherManager from './v26/VoucherManager';
import EventsManager from './v26/EventsManager';
import StaffAvailability from './v26/StaffAvailability';
import GiftCardSale from './v26/GiftCardSale';
import MarketingEmails from './v26/MarketingEmails';

export {
  Barcode128,
  VoucherManager,
  EventsManager,
  StaffAvailability,
  GiftCardSale,
  MarketingEmails,
};
