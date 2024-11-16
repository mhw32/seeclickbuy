export type Click = {
  click_id: string;
  image_url?: string;
  image_size?: [number, number];
  click?: [number, number];
  selection?: [number, number, number, number];
  user_id?: string;
  masked_url?: string;
  masked_size?: [number, number];
  bbox?: [number, number, number, number];
  segm?: number[];
  description?: string;
  channel?: string;
  version?: number;
  is_processed: boolean;
  created_at: number;
  updated_at: number;
}

export type ClickWithItems = Click & {
  items: Item[];
}

export type Chat = {
  chat_id: string;
  click_id: string;
  text: string;
  pre_description: string;
  post_description: string;
  created_at: number;
  updated_at: number;
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
  version?: number;
  created_at: number;
  updated_at: number;
}
