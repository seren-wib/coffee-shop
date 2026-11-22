import TextField from "./TextField";

// Address inputs shared by checkout (new address) and the address book (SDD 6.6, 6.11).
// The zip code is typed in; no address search service (SDD 6.11).
export default function AddressFields({ value, onChange, errors = {} }) {
  const set = (key) => (event) =>
    onChange({ ...value, [key]: event.target.value });
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
      <TextField
        label="받는 사람"
        required
        autoComplete="name"
        value={value.recipient_name}
        onChange={set("recipient_name")}
        error={errors.recipient_name}
      />
      <TextField
        label="연락처"
        required
        type="tel"
        autoComplete="tel"
        placeholder="010-0000-0000"
        value={value.recipient_phone}
        onChange={set("recipient_phone")}
        error={errors.recipient_phone}
      />
      <TextField
        label="우편번호"
        required
        inputMode="numeric"
        autoComplete="postal-code"
        maxLength={5}
        value={value.zipcode}
        onChange={set("zipcode")}
        error={errors.zipcode}
      />
      <TextField
        label="주소"
        required
        autoComplete="address-line1"
        className="col-span-full"
        value={value.base_address}
        onChange={set("base_address")}
        error={errors.base_address}
      />
      <TextField
        label="상세 주소"
        autoComplete="address-line2"
        className="col-span-full"
        value={value.detail_address}
        onChange={set("detail_address")}
        error={errors.detail_address}
      />
    </div>
  );
}
