export type AssetFormField = {
  key: string; label: string; required?: boolean; options?: string[];
  optionLabels?: Record<string, string>; optionDescriptions?: Record<string, string>;
  type?: 'textarea' | 'date' | 'number' | 'multi'; placeholder?: string; hint?: string;
  wide?: boolean; unitKey?: string; integer?: boolean; readonly?: boolean
}
