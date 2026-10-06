/**
 * Labelled text field built on Material UI with Tailwind layout classes.
 *
 * A thin wrapper: MUI handles the input, Tailwind handles the layout, and
 * `FormError` renders the validation message beneath the control. The props
 * below are the whole surface the login and register forms rely on.
 */

import { TextField } from '@mui/material';

import FormError from './FormError';

/**
 * Render a form control.
 *
 * @param {{
 *   label: string,
 *   name: string,
 *   value: string,
 *   onChange: (event: React.ChangeEvent<HTMLInputElement>) => void,
 *   onBlur?: (event: React.FocusEvent<HTMLInputElement>) => void,
 *   error?: string,
 *   helperText?: string,
 *   type?: string,
 *   required?: boolean,
 *   autoComplete?: string,
 *   disabled?: boolean,
 *   autoFocus?: boolean,
 *   ariaLabel?: string,
 *   ariaDescribedBy?: string,
 *   endAdornment?: React.ReactNode,
 *   inputRef?: React.Ref<HTMLInputElement>,
 * }} props Component props.
 * @returns {JSX.Element} The field.
 */
export default function FormInput({
  label,
  name,
  value,
  onChange,
  onBlur,
  error,
  helperText,
  type = 'text',
  required = false,
  autoComplete,
  disabled = false,
  autoFocus = false,
  ariaLabel,
  ariaDescribedBy,
  endAdornment,
  inputRef,
}) {
  // The message lives next to the control, so the control can reference it.
  const errorId = `${name}-error`;

  return (
    <div className="w-full">
      <TextField
        id={name}
        name={name}
        label={label}
        type={type}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        required={required}
        autoComplete={autoComplete}
        disabled={disabled}
        autoFocus={autoFocus}
        fullWidth
        size="medium"
        error={Boolean(error)}
        helperText={helperText}
        FormHelperTextProps={{ component: 'div' }}
        InputProps={{ endAdornment }}
        inputRef={inputRef}
        inputProps={{
          'aria-label': ariaLabel ?? label,
          'aria-invalid': error ? 'true' : undefined,
          'aria-describedby': ariaDescribedBy ?? (error ? errorId : undefined),
        }}
      />
      <FormError id={errorId} message={error} />
    </div>
  );
}
