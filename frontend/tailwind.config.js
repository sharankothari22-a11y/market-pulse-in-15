/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
  	extend: {
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			bi: {
  				'bg-page':       'var(--bi-bg-page)',
  				'bg-card':       'var(--bi-bg-card)',
  				'bg-subtle':     'var(--bi-bg-subtle)',
  				'border-subtle': 'var(--bi-border-subtle)',
  				'border-strong': 'var(--bi-border-strong)',
  				'navy-900':      'var(--bi-navy-900)',
  				'navy-700':      'var(--bi-navy-700)',
  				'navy-500':      'var(--bi-navy-500)',
  				'navy-100':      'var(--bi-navy-100)',
  				'text-primary':   'var(--bi-text-primary)',
  				'text-secondary': 'var(--bi-text-secondary)',
  				'text-tertiary':  'var(--bi-text-tertiary)',
  				'text-inverse':   'var(--bi-text-inverse)',
  				'tile-navy-bg':  'var(--bi-tile-navy-bg)',
  				'tile-navy-fg':  'var(--bi-tile-navy-fg)',
  				'tile-sage-bg':  'var(--bi-tile-sage-bg)',
  				'tile-sage-fg':  'var(--bi-tile-sage-fg)',
  				'tile-ochre-bg': 'var(--bi-tile-ochre-bg)',
  				'tile-ochre-fg': 'var(--bi-tile-ochre-fg)',
  				'tile-slate-bg': 'var(--bi-tile-slate-bg)',
  				'tile-slate-fg': 'var(--bi-tile-slate-fg)',
  				'success-fg': 'var(--bi-success-fg)',
  				'success-bg': 'var(--bi-success-bg)',
  				'danger-fg':  'var(--bi-danger-fg)',
  				'danger-bg':  'var(--bi-danger-bg)',
  				'warning-fg': 'var(--bi-warning-fg)',
  				'warning-bg': 'var(--bi-warning-bg)',
  			},
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};