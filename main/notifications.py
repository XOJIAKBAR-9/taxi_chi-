def build_driver_lost_item_notification(item_description, vehicle_model):
    """Message shown to the driver when a passenger reports a lost item."""
    return f"Did you find a {item_description} in your {vehicle_model}?"


def build_passenger_report_submitted_message(item_description):
    """Confirmation shown to the passenger after filing a report."""
    return f'Your lost item report for "{item_description}" has been sent to your driver.'


def build_passenger_found_message(item_description, driver_name):
    """Message shown to the passenger when the driver found the item."""
    return f"Good news! Driver {driver_name} found your {item_description}."


def build_passenger_not_found_message(item_description, driver_name):
    """Message shown to the passenger when the driver did not find the item."""
    return f"Driver {driver_name} could not find your {item_description} in the vehicle."
