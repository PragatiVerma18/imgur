from collections.abc import Collection
import datetime
from io import BytesIO
import math
import re
from typing import List, Tuple
from urllib import parse as urllib_parse

import requests
from PIL import Image
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.template.loader import render_to_string
from django.utils import dateformat, timezone


def get_serializer_field_errors(serializer_errors, is_root=True):
    """
    Parse field error messages from serializer and
    return them as a dict. Only the first error of
    a field gets included in the dict
    Args:
        serializer_errors:
        is_root:
    Returns:
        (dict)
    """
    field_errors = {}
    for field, errors in serializer_errors.items():
        if field == "non_field_errors":
            if is_root:
                continue
            else:
                return errors[0]
        if isinstance(errors, dict):
            field_errors[field] = get_serializer_field_errors(errors, is_root=False)
        elif isinstance(errors[0], dict):
            field_errors[field] = get_serializer_field_errors(errors[0], is_root=False)
        else:
            field_errors[field] = str(errors[0])
    return field_errors


def get_serializer_error(serializer):
    """
    Parse error message from serializer
    Args:
        serializer:
    Returns:
        (str)
    """
    return serializer.errors.get("non_field_errors", [""])[0]


def cast_to_int_gracefully(input_value, default_output=None):
    try:
        return int(input_value)
    except (TypeError, ValueError):
        return default_output


def cast_to_boolean(input_value: str) -> bool:
    if not isinstance(input_value, str):
        raise TypeError("Input value must be a string")

    true_values = ["yes", "true", "1"]
    false_values = ["no", "false", "0"]

    if input_value.lower() in true_values:
        return True
    elif input_value.lower() in false_values:
        return False
    else:
        raise ValueError("Invalid input value")


def remove_non_numeric_characters_from_string(input_string):
    return re.sub("[^0-9]", "", input_string)


def remove_leading_zeros_from_digit_string(input_string: str) -> str:
    if input_string.isdigit() and input_string.startswith("0"):
        return str(int(input_string))
    return input_string


def remove_trailing_zeros_from_digit_string(input_string: str) -> str:
    return str(float(input_string)).rstrip("0").rstrip(".")


def format_currency_amount(currency, amount, strip_decimals=False):
    formatted_amount = format_currency(amount, currency=currency, locale="en_IN")
    if strip_decimals:
        formatted_amount = formatted_amount[:-3]
    return formatted_amount


def format_inr_amount(amount, strip_decimals=False):
    return format_currency_amount(
        currency="INR",
        amount=amount,
        strip_decimals=strip_decimals,
    )


def get_human_readable_date_relative_delta(delta):
    formatted_year_part = "{years}y".format(years=delta.years) if delta.years else None
    formatted_month_part = (
        "{months}m".format(months=delta.months) if delta.months else None
    )
    return " ".join(filter(None, [formatted_year_part, formatted_month_part]))


def get_human_readable_file_size(size_in_bytes, separator=""):
    if size_in_bytes is None:
        return ""
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(round(size_in_bytes)) < 1000.0:
            return f"{size_in_bytes:3.1f}{separator}{unit}B"
        size_in_bytes /= 1000.0
    return f"{size_in_bytes:.1f}{separator}YB"


def relative_delta_to_fractional_years(delta):
    years = delta.years
    fractional_months = delta.months / 12
    fractional_days = delta.days / 365
    return round((years + fractional_months + fractional_days), 2)


def convert_currency_string_to_int(currency):
    INR_TO_DOLLAR = 1 / 70
    EURO_TO_DOLLAR = 1.12

    scale_map = {
        "k": 10**3,
        "m": 10**6,
        "b": 10**9,
        "t": 10**12,
    }
    money_regex = re.compile(r"(₹|\$|€|)([\d.]+)(k|m|b|t|)", re.UNICODE)
    currency = currency.lower()
    currency = currency.replace(",", "")
    match = money_regex.findall(currency)
    if match:
        match = match[0]
        value = float(match[1])
        if match[2]:
            value = value * scale_map[match[2]]
        if match[0] == "₹":
            value = int(value * INR_TO_DOLLAR)
        if match[0] == "€":
            value = int(value * EURO_TO_DOLLAR)
        return int(value)
    return 0


def fetch_remote_file(url, allow_redirects=False, timeout=30) -> BytesIO:
    try:
        response = requests.get(url, allow_redirects=allow_redirects, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise Exception("Failed to fetch remote file: {0}".format(url)) from e
    if not response.ok:
        raise Exception(
            "Request to fetch remote file ({0}) failed with status code: {1}".format(
                url, response.status_code
            )
        )
    try:
        file = BytesIO(response.content)
    except Exception as e:
        raise Exception(
            "Failed to create BytesIO object from response: {0}".format(url)
        ) from e
    return file


def fetch_remote_image(
    image_url, allow_redirects=False, timeout=30
) -> Tuple[BytesIO, Image]:
    image_file_bytes = fetch_remote_file(
        image_url, allow_redirects=allow_redirects, timeout=timeout
    )
    try:
        image = Image.open(image_file_bytes)
    except Exception as e:
        raise Exception(
            "Failed to create Image object from image url: {0}".format(image_url)
        ) from e
    return image_file_bytes, image


def square_crop_image(image: Image):
    width, height = image.size

    if width == height:
        return image

    if height < width:
        # make square by cutting off equal amounts left and right
        left = int(math.ceil((width - height) / 2))
        right = width - int(math.floor((width - height) / 2))
        top = 0
        bottom = height
        return image.crop((left, top, right, bottom))
    else:
        # make square by cutting off equal amounts top and bottom
        left = 0
        right = width
        top = int(math.floor((height - width) / 2))
        bottom = height - int(math.ceil((height - width) / 2))
        return image.crop((left, top, right, bottom))


def generate_user_full_name(first_name, last_name):
    return " ".join(filter(None, [first_name, last_name]))


def get_user_first_name_from_full_name(full_name):
    """
    This should ideally be avoided.
    Use it only if first_name is missing in the User object
    """
    if full_name:
        return full_name.split(" ")[0]
    return ""


def generate_avatar_image_file(source_image_file, max_size=1024, quality=85):
    image = Image.open(source_image_file)
    if image.width != image.height:
        image = square_crop_image(image)
    if image.width > max_size:
        image = image.resize((max_size, max_size))

    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    image_file = BytesIO()
    image.save(image_file, format="JPEG", quality=quality)
    image_file.seek(0)
    return image_file


def generate_avatar_size_variants_dict(s3_url, cloudinary_base_url, sizes=None) -> dict:
    if not sizes:
        sizes = [
            48,
            96,
            144,
            192,
            240,  # New sizes
            # 32, 64, 150, 300,  # Old sizes
        ]
    variants = {
        # 'thumbnail': {
        #     'url': f'{cloudinary_base_url}image/fetch/c_fill,w_150,ar_1:1,q_85/{s3_url}',
        # },
        # 'default': {
        #     'url': f'{cloudinary_base_url}image/fetch/c_fill,w_300,ar_1:1,q_85/{s3_url}',
        # },
    }
    for size in sizes:
        variants[f"{size}x{size}"] = {
            "url": f"{cloudinary_base_url}image/fetch/c_fill,w_{size},ar_1:1,q_85/{s3_url}",
        }
    return variants


def generate_og_image_file(source_image_file, quality=85):
    image = Image.open(source_image_file)

    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    image_file = BytesIO()
    image.save(image_file, format="JPEG", quality=quality)
    image_file.seek(0)
    return image_file


def get_now_ist():
    return datetime.datetime.now(get_ist_timezone())


def get_now_utc():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def get_min_datetime_utc():
    return datetime.datetime.utcnow().replace(
        year=1,
        month=1,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=pytz.utc,
    )


def utc_date_to_ist_date(utc_dt):
    return utc_dt.replace(tzinfo=pytz.utc).astimezone(get_ist_timezone())


def format_date(dt, format_str):
    df = dateformat.DateFormat(dt)
    return df.format(format_str)


def calculate_number_of_weeks_between_dates(start_date, end_date):
    return int(math.floor((end_date - start_date).days / 7))


def get_start_of_day(dt: datetime.datetime) -> datetime.datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_end_of_day(dt: datetime.datetime) -> datetime.datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def get_start_and_end_of_day(
    dt: datetime.datetime,
) -> (datetime.datetime, datetime.datetime):
    start_of_day = get_start_of_day(dt=dt)
    end_of_day = get_end_of_day(dt=dt)
    return start_of_day, end_of_day


def get_start_and_end_of_week(dt=datetime.datetime.now()):
    start_of_week = (dt - datetime.timedelta(days=dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end_of_week = (start_of_week + datetime.timedelta(days=6)).replace(
        hour=23, minute=59, second=59, microsecond=999999
    )
    return start_of_week, end_of_week


def fuzzy_fix_email_address(email: str) -> str:
    email_domain = email.split("@")[1]
    for domain in ["gmail.com"]:
        if domain != email_domain and fuzz.ratio(domain, email_domain) > 85:
            # There is a typo
            return email.replace(f"@{email_domain}", f"@{domain}")
    return email


def is_test_email_address(email):
    return email.endswith("@upraised.co")


def is_test_phone_number(country_code, phone):
    return country_code == "+91" and phone.startswith("1")


def calculate_percentage(value, total, precision=2):
    if not total:
        return 0
    return round(value / total * 100, precision)


def render_email(template_name, context=None, request=None):
    from shenron.lib.context_processors import shenron_global as shenron_global_context

    final_context = {
        **shenron_global_context(request=request),
        **(context if context else {}),
    }
    return render_to_string(
        template_name=template_name,
        context=final_context,
        request=request,
    )


def is_valid_url(url):
    url_validate = URLValidator()
    try:
        url_validate(url)
    except ValidationError:
        return False
    return True


def mimetype_to_extension(mimetype: str):
    ext = mimetypes.guess_extension(mimetype)
    if ext and isinstance(ext, str) and ext.startswith("."):
        ext = ext[1:]
    return ext


def generate_s3_object_url(bucket: str, region: str, key: str):
    if key.startswith("/"):
        key = key[1:]
    return "https://{0}.s3.{1}.amazonaws.com/{2}".format(
        bucket,
        region,
        key,
    )


def is_valid_uuid(val, version=4):
    try:
        UUID(val, version=version)
        return True
    except ValueError:
        return False
    except TypeError:
        return False


def parse_time(t_str=""):
    """
    t_str = "10:00" | "10:00:00"
    returns a datetime.time
    """
    try:
        hour, minute = list(map(int, t_str.split(":")))
        return datetime.time(hour, minute)
    except ValueError:
        hour, minute, second = list(map(int, t_str.split(":")))
        return datetime.time(hour, minute, second)


def utm_params_have_some_value(utm_params: dict):
    for value in utm_params.values():
        if value:
            return True
    return False


def get_timezones():
    """
    Returns a list of supported timezones
    """
    timezones = list(pytz.all_timezones_set)
    timezones.sort()
    return timezones


def get_ist_timezone():
    return pytz.timezone("Asia/Kolkata")


def truncate_text(text, max_length=30, add_ellipsis=True):
    if len(text) > max_length:
        truncate_length = max_length
        if add_ellipsis:
            truncate_length = max_length - 3
        truncated_text = text[:truncate_length]
        return truncated_text + ("..." if add_ellipsis else "")
    return text


def pick_dict_keys(src_dict, keys: List = None):
    if not keys:
        keys = []
    return dict([(k, v) for k, v in src_dict.items() if k in keys])


def omit_dict_keys(src_dict, keys: List = None):
    if not keys:
        keys = []
    return dict([(k, v) for k, v in src_dict.items() if k not in keys])


def create_chunks(sized_iterable: Collection, chunk_size) -> list[list]:
    """
    Returns an iterable of equal sized chunks based on the chunk size
    """
    chunked_list = []
    for i in range(0, len(sized_iterable), chunk_size):
        chunked_list.append(sized_iterable[i : i + chunk_size])
    return chunked_list


def get_frozen_time(dt_to_freeze: timezone.datetime, tz=pytz.timezone("Asia/Kolkata")):
    return freeze_time(tz.localize(dt_to_freeze))


def get_class_var_values(klass) -> List:
    return [
        value
        for attr, value in klass.__dict__.items()
        if not callable(value) and not attr.startswith("__")
    ]


def get_class_var_attrs_and_values(klass) -> List:
    return [
        (attr, value)
        for attr, value in klass.__dict__.items()
        if not callable(value) and not attr.startswith("__")
    ]


def flatten_dict(d, parent_key="", sep="_"):
    """
    Recursively flattens a nested dictionary.

    Args:
        d (dict): The nested dictionary to be flattened.
        parent_key (str, optional): The parent key for nested keys. Default is an empty string.
        sep (str, optional): The separator used to join keys. Default is '_'.

    Returns:
        dict: The flattened dictionary.
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
