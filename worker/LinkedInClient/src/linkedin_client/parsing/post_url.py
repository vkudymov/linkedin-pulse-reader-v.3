"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_posts.parsing.post_url import (
    find_overflow_menu_button,
    open_overflow_menu,
    click_copy_link_menu_item,
    read_post_url_after_copy,
    close_any_open_menus,
    extract_post_url_from_dom,
    get_post_url,
)

__all__ = ['find_overflow_menu_button', 'open_overflow_menu', 'click_copy_link_menu_item', 'read_post_url_after_copy', 'close_any_open_menus', 'extract_post_url_from_dom', 'get_post_url']
