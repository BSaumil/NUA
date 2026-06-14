import React from 'react';
import { ChevronsUpDown } from 'lucide-react';
import { Popover, PopoverTrigger, PopoverContent } from '../ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '../ui/command';

/** Searchable customer combobox built on cmdk + shadcn Popover. */
export default function CustomerCombobox({ customers, onChange, theme }) {
  const [open, setOpen] = React.useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          role="combobox"
          aria-expanded={open}
          className="w-full flex items-center justify-between p-2 border rounded-md text-sm bg-white hover:border-gray-400 transition"
          data-testid="pos-customer-select"
        >
          <span className="text-gray-500">Walk-in Customer · search to assign</span>
          <ChevronsUpDown size={14} className="opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[380px] p-0" align="start">
        <Command shouldFilter={true}>
          <CommandInput placeholder="Search by name, email, phone…" data-testid="customer-search-input" />
          <CommandList className="max-h-[280px]">
            <CommandEmpty>No matching customer.</CommandEmpty>
            <CommandGroup>
              {customers.map(c => (
                <CommandItem
                  key={c.id}
                  value={`${c.name} ${c.email || ''} ${c.phone || ''} ${c.membershipTier || ''}`}
                  onSelect={() => { onChange(c); setOpen(false); }}
                  data-testid={`customer-option-${c.id}`}
                  className="cursor-pointer"
                >
                  <div className="flex flex-col w-full">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{c.name}</span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: `${theme.primary}15`, color: theme.primary }}>{c.membershipTier || 'Member'}</span>
                    </div>
                    {(c.email || c.phone) && <span className="text-xs text-gray-500">{c.email}{c.email && c.phone ? ' · ' : ''}{c.phone}</span>}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
