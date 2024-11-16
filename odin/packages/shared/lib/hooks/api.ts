const BASE_URL = "http://localhost:8000";

export type Click = {
  click_id: string;
  image_url: string;
  image_size: [number, number];
  click: [number, number];
  user_id?: string;
  masked_url?: string;
  masked_size?: [number, number];
  bbox?: [number, number, number, number];
  segm?: number[];
  description?: string;
  channel?: string;
  created_at: number;
  updated_at: number;
  is_processed: boolean;
}

export type Chat = {
  click_id: string;
  text: string;
  pre_description: string;
  post_description: string;
  created_at: number;
  updated_at: number;
}

export type ClickCreate = {
  base64_image: string;
  click?: [number, number];
  selection?: [number, number, number, number];
  user_id?: string;
  channel?: string;
}

export type ChatCreate = {
  click_id: string;
  text: string;
}

export type Item = {
  item_id: string;
  click_id: string;
  title: string;
  link: string;
  source: string;
  source_icon?: string;
  price_value: number;
  price_currency: string;
  thumbnail?: string;
  in_stock: boolean;
  is_favorite: boolean;
  created_at: number;
  updated_at: number;
}

/**
 * Fetch a item by id
 * @param itemId (string) - The id of the item
 * @returns (Item) - The item
 */
export const fetchItem = async (itemId: string): Promise<Item> => {
  return fetch(`${BASE_URL}/item/${itemId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
  .then((res) => res.json())
  .catch((err) => console.error(err));
}

/**
 * Fetch a click by id
 * @param clickId (string) - The id of the click
 * @returns (Click) - The click
 */
export const fetchClick = async (clickId: string): Promise<Click> => {
  return fetch(`${BASE_URL}/click/${clickId}`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
    },
  })
  .then(res => res.json())
  .catch((err) => console.error(err));
}

// chat
// POST /chat
// input body { click_id: string, text: string }
// response, it will reset click.is_processed = false, then repeat fetch results

/**
 * Fetch items for a given click
 * @param clickId (string) - The id of the click
 * @param limit (number) - The maximum number of items to return
 * @returns (Item[]) - The items
 */
export const fetchClickItems = async (clickId: string, limit: number = 10): Promise<Item[]> => {
  return fetch(`${BASE_URL}/click/${clickId}/items?limit=${limit}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
  .then((res) => res.json())
  .catch((err) => console.error(err));
}

/**
 * Fetch favorited items for a given click
 * @param clickId (string) - The id of the click
 * @param limit (number) - The maximum number of items to return
 * @returns (Item[]) - The items
 */
export const fetchClickFavoriteItems = async (clickId: string, limit: number = 10): Promise<Item[]> => {
  return fetch(`${BASE_URL}/click/${clickId}/items/favorites?limit=${limit}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
  .then((res) => res.json())
  .catch((err) => console.error(err));
}

/**
 * Fetch recent clicks for a given user
 * @param userId (string) - The id of the user
 * @param limit (number) - The maximum number of clicks to return
 * @returns (Click[]) - The clicks
 */
export const fetchRecentClicks = async (userId: string, limit: number = 10): Promise<Click[]> => {
  return fetch(`${BASE_URL}/user/${userId}/clicks?limit=${limit}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
  .then((res) => res.json())
  .catch((err) => console.error(err));
}

// POST requests

/**
 * Create a click
 * @param click (ClickCreate) - The click to create
 * @returns (Click) - The created click
 */
export const createClick = async (click: ClickCreate): Promise<Click> => {
  return fetch(`${BASE_URL}/click`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(click),
  })
  .then((res) => res.json())
  .catch((err) => console.error(err));
}

/**
 * Create a chat
 */
export const createChat = async (chat: ChatCreate): Promise<[Click, Chat]> => {
  return fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(chat),
  })
  .then((res) => res.json())
  .catch((err) => console.error(err));
}

/**
 * Favorite an item
 * @param itemId (string) - The id of the item
 * @returns (Item) - The updated item
 */
export const favorite = async (itemId: string): Promise<Item> => {
  return fetch(`${BASE_URL}/item/${itemId}/favorite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
  .then((res) => res.json())
  .catch((err) => console.error(err));
}

/**
 * Unfavorite an item
 * @param itemId (string) - The id of the item
 * @returns (Item) - The updated item
 */
export const unfavorite = async (itemId: string): Promise<Item> => {
  return fetch(`${BASE_URL}/item/${itemId}/unfavorite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
  .then((res) => res.json())
  .catch((err) => console.error(err));
}