import { useEffect, useRef } from 'react';

const SVG_MARKUP = `
<svg id="bi8" width="100%" viewBox="0 0 680 500" role="img" style="display:block; border-radius:10px; background:#050A07;">
  <title>Beaver Intelligence command center with Manhattan skyline and 5-stage research workflow timeline</title>
  <desc>Cinematic 15-second scene of an analyst at a six-monitor command center overlooking New York with Empire State Building, NYSE, and Brooklyn Bridge. A 5-stage workflow timeline at the bottom progresses from data fetching to final report.</desc>

  <defs>
    <linearGradient id="sky8" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0A1A14"/>
      <stop offset="30%" stop-color="#0F2E20"/>
      <stop offset="60%" stop-color="#264035"/>
      <stop offset="85%" stop-color="#D4A24C"/>
      <stop offset="100%" stop-color="#F4C26B"/>
    </linearGradient>
    <linearGradient id="bldgFar8" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1F3A2D"/>
      <stop offset="100%" stop-color="#2E5644"/>
    </linearGradient>
    <linearGradient id="bldgMid8" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0F2118"/>
      <stop offset="100%" stop-color="#1A3025"/>
    </linearGradient>
    <linearGradient id="bldgNear8" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#050C08"/>
      <stop offset="100%" stop-color="#0A1812"/>
    </linearGradient>
    <linearGradient id="floor8" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0A1510"/>
      <stop offset="100%" stop-color="#020604"/>
    </linearGradient>
    <linearGradient id="desk8" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#3A2818"/>
      <stop offset="100%" stop-color="#1A1108"/>
    </linearGradient>
    <radialGradient id="screenGlow8" cx="0.5" cy="0.5" r="0.6">
      <stop offset="0%" stop-color="#D4A24C" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#D4A24C" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="amberAccent8" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#D4A24C"/>
      <stop offset="50%" stop-color="#F4C26B"/>
      <stop offset="100%" stop-color="#D4A24C"/>
    </linearGradient>

    <clipPath id="winC8"><rect x="20" y="20" width="640" height="240" rx="2"/></clipPath>

    <clipPath id="u1"><rect x="60" y="200" width="100" height="60" rx="1"/></clipPath>
    <clipPath id="u2"><rect x="170" y="200" width="100" height="60" rx="1"/></clipPath>
    <clipPath id="u3"><rect x="280" y="200" width="100" height="60" rx="1"/></clipPath>
    <clipPath id="u4"><rect x="390" y="200" width="100" height="60" rx="1"/></clipPath>
    <clipPath id="u5"><rect x="500" y="200" width="100" height="60" rx="1"/></clipPath>
    <clipPath id="u6"><rect x="225" y="270" width="230" height="80" rx="1"/></clipPath>
  </defs>

  <rect x="0" y="0" width="680" height="500" fill="#050A07"/>

  <g clip-path="url(#winC8)">
    <rect x="20" y="20" width="640" height="240" fill="url(#sky8)"/>

    <ellipse cx="450" cy="200" rx="220" ry="22" fill="#F4C26B" opacity="0.35"/>
    <ellipse cx="450" cy="200" rx="100" ry="10" fill="#F4D88A" opacity="0.55"/>

    <g fill="#D4A24C" opacity="0.2">
      <ellipse cx="120" cy="80" rx="60" ry="3"/>
      <ellipse cx="300" cy="65" rx="80" ry="2.5"/>
      <ellipse cx="500" cy="92" rx="70" ry="3"/>
      <ellipse cx="600" cy="60" rx="40" ry="2"/>
    </g>

    <g fill="url(#bldgFar8)">
      <rect x="20" y="155" width="35" height="105"/>
      <rect x="55" y="145" width="28" height="115"/>
      <rect x="83" y="160" width="32" height="100"/>
      <rect x="115" y="150" width="26" height="110"/>
      <rect x="141" y="165" width="38" height="95"/>
      <rect x="179" y="155" width="30" height="105"/>
      <rect x="209" y="170" width="42" height="90"/>
      <rect x="251" y="160" width="34" height="100"/>
      <rect x="285" y="150" width="40" height="110"/>

      <rect x="320" y="170" width="6" height="90"/>
      <polygon points="320,170 323,162 326,170"/>
      <rect x="321.5" y="178" width="3" height="6" fill="#0A1A14"/>
      <rect x="321.5" y="190" width="3" height="6" fill="#0A1A14"/>
      <path d="M 326 174 Q 360 200 394 174" stroke="#1F3A2D" stroke-width="1.2" fill="none"/>
      <path d="M 326 188 L 394 188" stroke="#1F3A2D" stroke-width="0.8" fill="none"/>
      <path d="M 330 188 L 332 174 M 338 188 L 339 178 M 346 188 L 346 180 M 354 188 L 354 180 M 362 188 L 362 180 M 370 188 L 370 180 M 378 188 L 379 178 M 386 188 L 388 174" stroke="#1F3A2D" stroke-width="0.4"/>
      <rect x="394" y="170" width="6" height="90"/>
      <polygon points="394,170 397,162 400,170"/>
      <rect x="395.5" y="178" width="3" height="6" fill="#0A1A14"/>
      <rect x="395.5" y="190" width="3" height="6" fill="#0A1A14"/>

      <rect x="402" y="170" width="36" height="90"/>
      <rect x="438" y="180" width="30" height="80"/>
      <rect x="468" y="165" width="38" height="95"/>
      <rect x="506" y="175" width="32" height="85"/>
      <rect x="538" y="160" width="40" height="100"/>
      <rect x="578" y="170" width="34" height="90"/>
      <rect x="612" y="180" width="48" height="80"/>
    </g>

    <g fill="url(#bldgMid8)">
      <rect x="30" y="120" width="42" height="140"/>
      <rect x="74" y="100" width="36" height="160"/>
      <rect x="112" y="130" width="48" height="130"/>
      <rect x="162" y="115" width="38" height="145"/>

      <g>
        <rect x="180" y="178" width="64" height="82" fill="#1A3025"/>
        <rect x="178" y="252" width="68" height="8" fill="#2A4A38"/>
        <rect x="186" y="190" width="3" height="62" fill="#264035"/>
        <rect x="195" y="190" width="3" height="62" fill="#264035"/>
        <rect x="204" y="190" width="3" height="62" fill="#264035"/>
        <rect x="213" y="190" width="3" height="62" fill="#264035"/>
        <rect x="222" y="190" width="3" height="62" fill="#264035"/>
        <rect x="231" y="190" width="3" height="62" fill="#264035"/>
        <rect x="180" y="184" width="64" height="6" fill="#0F2118"/>
        <polygon points="180,184 212,162 244,184" fill="#0F2118"/>
        <polygon points="184,184 212,166 240,184" fill="none" stroke="#264035" stroke-width="0.4"/>
        <rect x="178" y="256" width="68" height="2" fill="#0F2118"/>
        <g>
          <rect x="184" y="190" width="56" height="34" fill="#FAF6EC" opacity="0.95"/>
          <rect x="184" y="190" width="56" height="3" fill="#A32D2D"/>
          <rect x="184" y="196" width="56" height="3" fill="#A32D2D"/>
          <rect x="184" y="202" width="56" height="3" fill="#A32D2D"/>
          <rect x="184" y="208" width="56" height="3" fill="#A32D2D"/>
          <rect x="184" y="214" width="56" height="3" fill="#A32D2D"/>
          <rect x="184" y="220" width="56" height="3" fill="#A32D2D"/>
          <rect x="184" y="190" width="22" height="14" fill="#185FA5"/>
          <g fill="#FAF6EC">
            <circle cx="187" cy="193" r="0.4"/><circle cx="190" cy="193" r="0.4"/><circle cx="193" cy="193" r="0.4"/><circle cx="196" cy="193" r="0.4"/><circle cx="199" cy="193" r="0.4"/><circle cx="202" cy="193" r="0.4"/>
            <circle cx="188.5" cy="196" r="0.4"/><circle cx="191.5" cy="196" r="0.4"/><circle cx="194.5" cy="196" r="0.4"/><circle cx="197.5" cy="196" r="0.4"/><circle cx="200.5" cy="196" r="0.4"/>
            <circle cx="187" cy="199" r="0.4"/><circle cx="190" cy="199" r="0.4"/><circle cx="193" cy="199" r="0.4"/><circle cx="196" cy="199" r="0.4"/><circle cx="199" cy="199" r="0.4"/><circle cx="202" cy="199" r="0.4"/>
            <circle cx="188.5" cy="202" r="0.4"/><circle cx="191.5" cy="202" r="0.4"/><circle cx="194.5" cy="202" r="0.4"/><circle cx="197.5" cy="202" r="0.4"/><circle cx="200.5" cy="202" r="0.4"/>
          </g>
        </g>
        <text x="212" y="180" text-anchor="middle" font-family="serif" font-size="3.4" fill="#D4A24C" font-weight="700" letter-spacing="0.3">NYSE</text>
        <rect x="211" y="148" width="1.2" height="14" fill="#3A2818"/>
        <path d="M 212.2 148 L 220 150 L 212.2 152 Z" fill="#A32D2D"/>
      </g>

      <g>
        <rect x="260" y="80" width="44" height="180" fill="#1A3025"/>
        <rect x="266" y="65" width="32" height="20" fill="#1A3025"/>
        <rect x="270" y="50" width="24" height="18" fill="#1A3025"/>
        <polygon points="270,50 282,30 294,50" fill="#1A3025"/>
        <rect x="280.5" y="14" width="3" height="18" fill="#0F2118"/>
        <rect x="281.5" y="6" width="1" height="10" fill="#0F2118"/>
        <circle cx="282" cy="6" r="1.2" fill="#E84545">
          <animate attributeName="opacity" values="1;0.2;1" dur="1.5s" repeatCount="indefinite"/>
        </circle>
        <rect x="271" y="50" width="22" height="15" fill="#D4A24C" opacity="0.55"/>
        <rect x="267" y="65" width="30" height="20" fill="#D4A24C" opacity="0.4"/>
        <ellipse cx="282" cy="40" rx="22" ry="6" fill="#F4C26B" opacity="0.18"/>
      </g>

      <polygon points="425,90 437,90 442,260 420,260" fill="#1A3025"/>
      <rect x="429" y="50" width="4" height="40" fill="#1A3025"/>
      <rect x="430" y="20" width="2" height="30" fill="#0F2118"/>
      <circle cx="431" cy="22" r="1.2" fill="#E84545">
        <animate attributeName="opacity" values="0.2;1;0.2" dur="1.8s" repeatCount="indefinite"/>
      </circle>

      <rect x="335" y="100" width="36" height="160" fill="#1A3025"/>
      <polygon points="335,100 353,55 371,100" fill="#0F2118"/>
      <rect x="351" y="35" width="4" height="22" fill="#0F2118"/>

      <rect x="380" y="115" width="44" height="145" fill="#1A3025"/>
      <rect x="447" y="120" width="38" height="140" fill="#1A3025"/>
      <rect x="487" y="110" width="42" height="150" fill="#1A3025"/>
      <rect x="532" y="125" width="36" height="135" fill="#1A3025"/>
      <rect x="572" y="115" width="44" height="145" fill="#1A3025"/>
      <rect x="618" y="130" width="42" height="130" fill="#1A3025"/>
    </g>

    <g fill="url(#bldgNear8)">
      <rect x="20" y="170" width="55" height="90"/>
      <rect x="148" y="160" width="32" height="100"/>
      <rect x="555" y="165" width="58" height="95"/>
    </g>

    <g fill="#F4C26B" opacity="0.85">
      <g>
        <rect x="265" y="100" width="1.5" height="1.5"/><rect x="270" y="100" width="1.5" height="1.5"/><rect x="275" y="100" width="1.5" height="1.5"/><rect x="280" y="100" width="1.5" height="1.5"/><rect x="285" y="100" width="1.5" height="1.5"/><rect x="290" y="100" width="1.5" height="1.5"/><rect x="295" y="100" width="1.5" height="1.5"/><rect x="300" y="100" width="1.5" height="1.5"/>
        <rect x="265" y="110" width="1.5" height="1.5"/><rect x="275" y="110" width="1.5" height="1.5"/><rect x="285" y="110" width="1.5" height="1.5"/><rect x="295" y="110" width="1.5" height="1.5"/>
        <rect x="270" y="120" width="1.5" height="1.5"/><rect x="280" y="120" width="1.5" height="1.5"/><rect x="290" y="120" width="1.5" height="1.5"/><rect x="300" y="120" width="1.5" height="1.5"/>
        <rect x="265" y="130" width="1.5" height="1.5"/><rect x="275" y="130" width="1.5" height="1.5"/><rect x="285" y="130" width="1.5" height="1.5"/><rect x="295" y="130" width="1.5" height="1.5"/>
        <rect x="270" y="140" width="1.5" height="1.5"/><rect x="280" y="140" width="1.5" height="1.5"/><rect x="290" y="140" width="1.5" height="1.5"/><rect x="300" y="140" width="1.5" height="1.5"/>
        <rect x="265" y="150" width="1.5" height="1.5"/><rect x="275" y="150" width="1.5" height="1.5"/><rect x="285" y="150" width="1.5" height="1.5"/><rect x="295" y="150" width="1.5" height="1.5"/>
        <rect x="270" y="170" width="1.5" height="1.5"/><rect x="280" y="170" width="1.5" height="1.5"/><rect x="290" y="170" width="1.5" height="1.5"/><rect x="300" y="170" width="1.5" height="1.5"/>
        <rect x="265" y="185" width="1.5" height="1.5"/><rect x="275" y="185" width="1.5" height="1.5"/><rect x="285" y="185" width="1.5" height="1.5"/><rect x="295" y="185" width="1.5" height="1.5"/>
        <rect x="270" y="200" width="1.5" height="1.5"/><rect x="280" y="200" width="1.5" height="1.5"/><rect x="290" y="200" width="1.5" height="1.5"/><rect x="300" y="200" width="1.5" height="1.5"/>
        <rect x="265" y="215" width="1.5" height="1.5"/><rect x="275" y="215" width="1.5" height="1.5"/><rect x="285" y="215" width="1.5" height="1.5"/><rect x="295" y="215" width="1.5" height="1.5"/>
        <rect x="270" y="230" width="1.5" height="1.5"/><rect x="280" y="230" width="1.5" height="1.5"/><rect x="290" y="230" width="1.5" height="1.5"/><rect x="300" y="230" width="1.5" height="1.5"/>
        <rect x="265" y="245" width="1.5" height="1.5"/><rect x="275" y="245" width="1.5" height="1.5"/><rect x="285" y="245" width="1.5" height="1.5"/><rect x="295" y="245" width="1.5" height="1.5"/>
      </g>

      <g>
        <rect x="35" y="135" width="1.5" height="1.5"/><rect x="45" y="135" width="1.5" height="1.5"/><rect x="55" y="135" width="1.5" height="1.5"/><rect x="65" y="135" width="1.5" height="1.5"/>
        <rect x="40" y="150" width="1.5" height="1.5"/><rect x="50" y="150" width="1.5" height="1.5"/><rect x="60" y="150" width="1.5" height="1.5"/>
        <rect x="35" y="165" width="1.5" height="1.5"/><rect x="45" y="165" width="1.5" height="1.5"/><rect x="55" y="165" width="1.5" height="1.5"/><rect x="65" y="165" width="1.5" height="1.5"/>
        <rect x="40" y="180" width="1.5" height="1.5"/><rect x="50" y="180" width="1.5" height="1.5"/><rect x="60" y="180" width="1.5" height="1.5"/>
        <rect x="35" y="195" width="1.5" height="1.5"/><rect x="45" y="195" width="1.5" height="1.5"/><rect x="55" y="195" width="1.5" height="1.5"/><rect x="65" y="195" width="1.5" height="1.5"/>
        <rect x="40" y="215" width="1.5" height="1.5"/><rect x="50" y="215" width="1.5" height="1.5"/><rect x="60" y="215" width="1.5" height="1.5"/>
        <rect x="35" y="235" width="1.5" height="1.5"/><rect x="45" y="235" width="1.5" height="1.5"/><rect x="55" y="235" width="1.5" height="1.5"/>

        <rect x="80" y="115" width="1.5" height="1.5"/><rect x="90" y="115" width="1.5" height="1.5"/><rect x="100" y="115" width="1.5" height="1.5"/>
        <rect x="85" y="130" width="1.5" height="1.5"/><rect x="95" y="130" width="1.5" height="1.5"/>
        <rect x="80" y="145" width="1.5" height="1.5"/><rect x="90" y="145" width="1.5" height="1.5"/><rect x="100" y="145" width="1.5" height="1.5"/>
        <rect x="85" y="160" width="1.5" height="1.5"/><rect x="95" y="160" width="1.5" height="1.5"/>
        <rect x="80" y="175" width="1.5" height="1.5"/><rect x="90" y="175" width="1.5" height="1.5"/><rect x="100" y="175" width="1.5" height="1.5"/>
        <rect x="85" y="195" width="1.5" height="1.5"/><rect x="95" y="195" width="1.5" height="1.5"/>
        <rect x="80" y="215" width="1.5" height="1.5"/><rect x="90" y="215" width="1.5" height="1.5"/><rect x="100" y="215" width="1.5" height="1.5"/>
        <rect x="85" y="235" width="1.5" height="1.5"/><rect x="95" y="235" width="1.5" height="1.5"/>

        <rect x="118" y="145" width="1.5" height="1.5"/><rect x="128" y="145" width="1.5" height="1.5"/><rect x="138" y="145" width="1.5" height="1.5"/><rect x="148" y="145" width="1.5" height="1.5"/>
        <rect x="123" y="160" width="1.5" height="1.5"/><rect x="133" y="160" width="1.5" height="1.5"/><rect x="143" y="160" width="1.5" height="1.5"/>
        <rect x="118" y="175" width="1.5" height="1.5"/><rect x="128" y="175" width="1.5" height="1.5"/><rect x="138" y="175" width="1.5" height="1.5"/>
        <rect x="123" y="195" width="1.5" height="1.5"/><rect x="133" y="195" width="1.5" height="1.5"/><rect x="143" y="195" width="1.5" height="1.5"/>
        <rect x="118" y="215" width="1.5" height="1.5"/><rect x="128" y="215" width="1.5" height="1.5"/><rect x="138" y="215" width="1.5" height="1.5"/>
        <rect x="123" y="235" width="1.5" height="1.5"/><rect x="133" y="235" width="1.5" height="1.5"/><rect x="143" y="235" width="1.5" height="1.5"/>

        <rect x="340" y="115" width="1.5" height="1.5"/><rect x="350" y="115" width="1.5" height="1.5"/><rect x="360" y="115" width="1.5" height="1.5"/>
        <rect x="345" y="130" width="1.5" height="1.5"/><rect x="355" y="130" width="1.5" height="1.5"/>
        <rect x="340" y="145" width="1.5" height="1.5"/><rect x="350" y="145" width="1.5" height="1.5"/><rect x="360" y="145" width="1.5" height="1.5"/>
        <rect x="345" y="160" width="1.5" height="1.5"/><rect x="355" y="160" width="1.5" height="1.5"/>
        <rect x="340" y="175" width="1.5" height="1.5"/><rect x="350" y="175" width="1.5" height="1.5"/><rect x="360" y="175" width="1.5" height="1.5"/>
        <rect x="345" y="195" width="1.5" height="1.5"/><rect x="355" y="195" width="1.5" height="1.5"/>
        <rect x="340" y="215" width="1.5" height="1.5"/><rect x="350" y="215" width="1.5" height="1.5"/><rect x="360" y="215" width="1.5" height="1.5"/>
        <rect x="345" y="235" width="1.5" height="1.5"/><rect x="355" y="235" width="1.5" height="1.5"/>

        <rect x="385" y="130" width="1.5" height="1.5"/><rect x="395" y="130" width="1.5" height="1.5"/><rect x="405" y="130" width="1.5" height="1.5"/><rect x="415" y="130" width="1.5" height="1.5"/>
        <rect x="390" y="145" width="1.5" height="1.5"/><rect x="400" y="145" width="1.5" height="1.5"/><rect x="410" y="145" width="1.5" height="1.5"/>
        <rect x="385" y="160" width="1.5" height="1.5"/><rect x="395" y="160" width="1.5" height="1.5"/><rect x="405" y="160" width="1.5" height="1.5"/><rect x="415" y="160" width="1.5" height="1.5"/>
        <rect x="390" y="180" width="1.5" height="1.5"/><rect x="400" y="180" width="1.5" height="1.5"/><rect x="410" y="180" width="1.5" height="1.5"/>
        <rect x="385" y="200" width="1.5" height="1.5"/><rect x="395" y="200" width="1.5" height="1.5"/><rect x="405" y="200" width="1.5" height="1.5"/>
        <rect x="390" y="220" width="1.5" height="1.5"/><rect x="400" y="220" width="1.5" height="1.5"/><rect x="410" y="220" width="1.5" height="1.5"/>
        <rect x="385" y="240" width="1.5" height="1.5"/><rect x="395" y="240" width="1.5" height="1.5"/><rect x="405" y="240" width="1.5" height="1.5"/>

        <rect x="450" y="135" width="1.5" height="1.5"/><rect x="460" y="135" width="1.5" height="1.5"/><rect x="470" y="135" width="1.5" height="1.5"/><rect x="478" y="135" width="1.5" height="1.5"/>
        <rect x="455" y="150" width="1.5" height="1.5"/><rect x="465" y="150" width="1.5" height="1.5"/><rect x="475" y="150" width="1.5" height="1.5"/>
        <rect x="450" y="165" width="1.5" height="1.5"/><rect x="460" y="165" width="1.5" height="1.5"/><rect x="470" y="165" width="1.5" height="1.5"/>
        <rect x="455" y="185" width="1.5" height="1.5"/><rect x="465" y="185" width="1.5" height="1.5"/><rect x="475" y="185" width="1.5" height="1.5"/>
        <rect x="450" y="205" width="1.5" height="1.5"/><rect x="460" y="205" width="1.5" height="1.5"/><rect x="470" y="205" width="1.5" height="1.5"/>
        <rect x="455" y="225" width="1.5" height="1.5"/><rect x="465" y="225" width="1.5" height="1.5"/><rect x="475" y="225" width="1.5" height="1.5"/>
        <rect x="450" y="245" width="1.5" height="1.5"/><rect x="460" y="245" width="1.5" height="1.5"/><rect x="470" y="245" width="1.5" height="1.5"/>

        <rect x="492" y="125" width="1.5" height="1.5"/><rect x="502" y="125" width="1.5" height="1.5"/><rect x="512" y="125" width="1.5" height="1.5"/><rect x="522" y="125" width="1.5" height="1.5"/>
        <rect x="497" y="140" width="1.5" height="1.5"/><rect x="507" y="140" width="1.5" height="1.5"/><rect x="517" y="140" width="1.5" height="1.5"/>
        <rect x="492" y="155" width="1.5" height="1.5"/><rect x="502" y="155" width="1.5" height="1.5"/><rect x="512" y="155" width="1.5" height="1.5"/>
        <rect x="497" y="175" width="1.5" height="1.5"/><rect x="507" y="175" width="1.5" height="1.5"/><rect x="517" y="175" width="1.5" height="1.5"/>
        <rect x="492" y="195" width="1.5" height="1.5"/><rect x="502" y="195" width="1.5" height="1.5"/><rect x="512" y="195" width="1.5" height="1.5"/>
        <rect x="497" y="215" width="1.5" height="1.5"/><rect x="507" y="215" width="1.5" height="1.5"/><rect x="517" y="215" width="1.5" height="1.5"/>
        <rect x="492" y="235" width="1.5" height="1.5"/><rect x="502" y="235" width="1.5" height="1.5"/><rect x="512" y="235" width="1.5" height="1.5"/>

        <rect x="540" y="140" width="1.5" height="1.5"/><rect x="550" y="140" width="1.5" height="1.5"/><rect x="560" y="140" width="1.5" height="1.5"/>
        <rect x="545" y="155" width="1.5" height="1.5"/><rect x="555" y="155" width="1.5" height="1.5"/>
        <rect x="540" y="170" width="1.5" height="1.5"/><rect x="550" y="170" width="1.5" height="1.5"/><rect x="560" y="170" width="1.5" height="1.5"/>
        <rect x="545" y="190" width="1.5" height="1.5"/><rect x="555" y="190" width="1.5" height="1.5"/>
        <rect x="540" y="210" width="1.5" height="1.5"/><rect x="550" y="210" width="1.5" height="1.5"/><rect x="560" y="210" width="1.5" height="1.5"/>
        <rect x="545" y="230" width="1.5" height="1.5"/><rect x="555" y="230" width="1.5" height="1.5"/>

        <rect x="580" y="130" width="1.5" height="1.5"/><rect x="590" y="130" width="1.5" height="1.5"/><rect x="600" y="130" width="1.5" height="1.5"/><rect x="610" y="130" width="1.5" height="1.5"/>
        <rect x="585" y="145" width="1.5" height="1.5"/><rect x="595" y="145" width="1.5" height="1.5"/><rect x="605" y="145" width="1.5" height="1.5"/>
        <rect x="580" y="160" width="1.5" height="1.5"/><rect x="590" y="160" width="1.5" height="1.5"/><rect x="600" y="160" width="1.5" height="1.5"/>
        <rect x="585" y="180" width="1.5" height="1.5"/><rect x="595" y="180" width="1.5" height="1.5"/><rect x="605" y="180" width="1.5" height="1.5"/>
        <rect x="580" y="200" width="1.5" height="1.5"/><rect x="590" y="200" width="1.5" height="1.5"/><rect x="600" y="200" width="1.5" height="1.5"/>
        <rect x="585" y="220" width="1.5" height="1.5"/><rect x="595" y="220" width="1.5" height="1.5"/><rect x="605" y="220" width="1.5" height="1.5"/>
        <rect x="580" y="240" width="1.5" height="1.5"/><rect x="590" y="240" width="1.5" height="1.5"/><rect x="600" y="240" width="1.5" height="1.5"/>

        <rect x="625" y="145" width="1.5" height="1.5"/><rect x="635" y="145" width="1.5" height="1.5"/><rect x="645" y="145" width="1.5" height="1.5"/>
        <rect x="630" y="160" width="1.5" height="1.5"/><rect x="640" y="160" width="1.5" height="1.5"/>
        <rect x="625" y="175" width="1.5" height="1.5"/><rect x="635" y="175" width="1.5" height="1.5"/><rect x="645" y="175" width="1.5" height="1.5"/>
        <rect x="630" y="195" width="1.5" height="1.5"/><rect x="640" y="195" width="1.5" height="1.5"/>
        <rect x="625" y="215" width="1.5" height="1.5"/><rect x="635" y="215" width="1.5" height="1.5"/><rect x="645" y="215" width="1.5" height="1.5"/>
        <rect x="630" y="235" width="1.5" height="1.5"/><rect x="640" y="235" width="1.5" height="1.5"/>
      </g>
    </g>
  </g>

  <rect x="20" y="20" width="640" height="240" rx="2" fill="none" stroke="#0F2118" stroke-width="2"/>
  <line x1="240" y1="20" x2="240" y2="260" stroke="#0F2118" stroke-width="1"/>
  <line x1="440" y1="20" x2="440" y2="260" stroke="#0F2118" stroke-width="1"/>

  <rect x="0" y="260" width="680" height="240" fill="url(#floor8)"/>
  <g opacity="0.12" clip-path="url(#winC8)">
    <g transform="translate(0,520) scale(1,-1)">
      <rect x="20" y="260" width="640" height="80" fill="url(#bldgMid8)"/>
    </g>
  </g>
  <rect x="0" y="260" width="680" height="2" fill="#D4A24C" opacity="0.25"/>

  <rect x="30" y="350" width="620" height="14" fill="url(#desk8)"/>
  <rect x="30" y="364" width="620" height="4" fill="#000"/>
  <rect x="30" y="368" width="6" height="50" fill="#1A1108"/>
  <rect x="644" y="368" width="6" height="50" fill="#1A1108"/>

  <rect x="105" y="262" width="2" height="88" fill="#0F2118"/>
  <rect x="215" y="262" width="2" height="88" fill="#0F2118"/>
  <rect x="325" y="262" width="2" height="88" fill="#0F2118"/>
  <rect x="435" y="262" width="2" height="88" fill="#0F2118"/>
  <rect x="545" y="262" width="2" height="88" fill="#0F2118"/>

  <g fill="#0A0A0A">
    <rect x="56" y="196" width="108" height="68" rx="2"/>
    <rect x="166" y="196" width="108" height="68" rx="2"/>
    <rect x="276" y="196" width="108" height="68" rx="2"/>
    <rect x="386" y="196" width="108" height="68" rx="2"/>
    <rect x="496" y="196" width="108" height="68" rx="2"/>
  </g>
  <rect x="221" y="266" width="238" height="88" rx="2" fill="#0A0A0A"/>

  <g fill="#D4A24C">
    <circle cx="110" cy="261.5" r="0.6"/>
    <circle cx="220" cy="261.5" r="0.6"/>
    <circle cx="330" cy="261.5" r="0.6"/>
    <circle cx="440" cy="261.5" r="0.6"/>
    <circle cx="550" cy="261.5" r="0.6"/>
    <circle cx="340" cy="356" r="0.6"/>
  </g>

  <g clip-path="url(#u1)">
    <rect x="60" y="200" width="100" height="60" fill="#050A07"/>
    <rect x="60" y="200" width="100" height="5" fill="#D4A24C"/>
    <text x="62" y="203.5" font-family="monospace" font-size="3" fill="#0F2E20" font-weight="700">BLOOMBERG · BEAVER</text>
    <g font-family="monospace" font-size="3" fill="#D4A24C">
      <text x="62" y="210">SPX    5,842.31  +0.42%</text>
      <text x="62" y="215">NDX   20,156.78  +0.61%</text>
      <text x="62" y="220">DJI   42,891.05  +0.18%</text>
      <text x="62" y="225" fill="#E84545">VIX      14.82  -2.15%</text>
      <text x="62" y="230">DXY     106.41  +0.08%</text>
      <text x="62" y="235">UST10Y   4.218</text>
      <text x="62" y="240">GOLD   2,684.5  +0.34%</text>
      <text x="62" y="245" fill="#E84545">WTI      71.22  -1.08%</text>
      <text x="62" y="250">BTC   98,421   +2.14%</text>
    </g>
    <line x1="62" y1="253" x2="158" y2="253" stroke="#264035" stroke-width="0.3"/>
    <text x="62" y="257" font-family="monospace" font-size="2.6" fill="#97C459">&gt; GO_</text>
    <rect x="73" y="255" width="1" height="2" fill="#97C459">
      <animate attributeName="opacity" values="1;0;1" dur="0.7s" repeatCount="indefinite"/>
    </rect>
  </g>

  <g clip-path="url(#u2)">
    <rect x="170" y="200" width="100" height="60" fill="#FAF6EC"/>
    <rect x="170" y="200" width="100" height="5" fill="#0F2E20"/>
    <circle cx="173" cy="202.5" r="0.8" fill="#D4A24C"/>
    <text x="175" y="203.7" font-family="sans-serif" font-size="2.6" fill="#FAF6EC" font-weight="600">Claude · Beaver Research</text>
    <text x="172" y="210" font-family="sans-serif" font-size="2.4" fill="#888">You</text>
    <rect x="172" y="211" width="80" height="8" rx="1" fill="#E8DCC4"/>
    <text x="174" y="214" font-family="sans-serif" font-size="2.4" fill="#0F2E20">Build a thesis on Indian</text>
    <text x="174" y="217" font-family="sans-serif" font-size="2.4" fill="#0F2E20">private banks for Q4</text>
    <text x="172" y="223" font-family="sans-serif" font-size="2.4" fill="#888">Claude</text>
    <rect x="172" y="224" width="96" height="34" rx="1" fill="#0F2E20"/>
    <text x="174" y="227" font-family="sans-serif" font-size="2.4" fill="#D4A24C" font-weight="600">Thesis · Indian Pvt Banks</text>
    <text x="174" y="231" font-family="sans-serif" font-size="2.3" fill="#FAF6EC">• HDFC: post-merger CASA</text>
    <text x="174" y="234.5" font-family="sans-serif" font-size="2.3" fill="#FAF6EC">  recovery, NIM expansion</text>
    <text x="174" y="238" font-family="sans-serif" font-size="2.3" fill="#FAF6EC">• ICICI: best ROA at 2.4%</text>
    <text x="174" y="241.5" font-family="sans-serif" font-size="2.3" fill="#FAF6EC">• Axis: turnaround story</text>
    <text x="174" y="245" font-family="sans-serif" font-size="2.3" fill="#FAF6EC">• Risk: unsecured retail</text>
    <text x="174" y="249" font-family="sans-serif" font-size="2.3" fill="#D4A24C">→ OW pvt vs PSU</text>
    <text x="174" y="252.5" font-family="sans-serif" font-size="2.3" fill="#D4A24C">→ Top: ICICI · 24% upside</text>
    <rect x="173.5" y="254" width="0.6" height="2" fill="#D4A24C">
      <animate attributeName="opacity" values="1;0;1" dur="0.6s" repeatCount="indefinite"/>
    </rect>
  </g>

  <g clip-path="url(#u3)">
    <rect x="280" y="200" width="100" height="60" fill="#0A1510"/>
    <rect x="280" y="200" width="100" height="5" fill="#0F2E20"/>
    <circle cx="282.5" cy="202.5" r="0.8" fill="#D4A24C"/>
    <circle cx="285.5" cy="202.5" r="0.8" fill="#97C459"/>
    <circle cx="288.5" cy="202.5" r="0.8" fill="#E84545"/>
    <text x="294" y="203.7" font-family="monospace" font-size="2.4" fill="#FAF6EC">backtest.py — beaver-intel</text>
    <g font-family="monospace" font-size="2.6">
      <text x="282" y="210" fill="#5F7A6C"> 1</text><text x="289" y="210" fill="#D4A24C">import</text><text x="301" y="210" fill="#FAF6EC">pandas</text><text x="313" y="210" fill="#D4A24C">as</text><text x="319" y="210" fill="#FAF6EC">pd</text>
      <text x="282" y="214" fill="#5F7A6C"> 2</text><text x="289" y="214" fill="#D4A24C">from</text><text x="297" y="214" fill="#FAF6EC">beaver</text><text x="310" y="214" fill="#D4A24C">import</text><text x="322" y="214" fill="#FAF6EC">Engine</text>
      <text x="282" y="218" fill="#5F7A6C"> 3</text>
      <text x="282" y="222" fill="#5F7A6C"> 4</text><text x="289" y="222" fill="#D4A24C">def</text><text x="297" y="222" fill="#F4C26B">backtest</text><text x="312" y="222" fill="#FAF6EC">(strategy):</text>
      <text x="282" y="226" fill="#5F7A6C"> 5</text><text x="293" y="226" fill="#FAF6EC">e</text><text x="295" y="226" fill="#D4A24C">=</text><text x="298" y="226" fill="#97C459">Engine</text><text x="312" y="226" fill="#FAF6EC">(</text><text x="313" y="226" fill="#F4C26B">"NSE_2020"</text><text x="332" y="226" fill="#FAF6EC">)</text>
      <text x="282" y="230" fill="#5F7A6C"> 6</text><text x="293" y="230" fill="#FAF6EC">r = e.run(strategy)</text>
      <text x="282" y="234" fill="#5F7A6C"> 7</text><text x="293" y="234" fill="#D4A24C">return</text><text x="307" y="234" fill="#FAF6EC">r.sharpe, r.cagr</text>
      <text x="282" y="238" fill="#5F7A6C"> 8</text>
      <text x="282" y="242" fill="#5F7A6C"> 9</text><text x="289" y="242" fill="#5F7A6C"># Sharpe 1.84 · CAGR 22.4%</text>
    </g>
    <rect x="280" y="246" width="100" height="14" fill="#050A07"/>
    <text x="282" y="250" font-family="monospace" font-size="2.4" fill="#97C459">$ python backtest.py</text>
    <text x="282" y="253.5" font-family="monospace" font-size="2.4" fill="#FAF6EC">processing 247 trades…</text>
    <text x="282" y="257" font-family="monospace" font-size="2.4" fill="#D4A24C">PnL +₹4.2L · Sharpe 1.84</text>
    <rect x="320" y="255" width="0.8" height="2" fill="#97C459">
      <animate attributeName="opacity" values="1;0;1" dur="0.6s" repeatCount="indefinite"/>
    </rect>
  </g>

  <g clip-path="url(#u4)">
    <rect x="390" y="200" width="100" height="60" fill="#FAF6EC"/>
    <rect x="390" y="200" width="100" height="5" fill="#0F2E20"/>
    <text x="392" y="203.5" font-family="sans-serif" font-size="2.6" fill="#D4A24C" font-weight="700">REUTERS</text>
    <text x="408" y="203.5" font-family="sans-serif" font-size="2.4" fill="#FAF6EC">· Markets · Live</text>
    <circle cx="485" cy="202.5" r="0.8" fill="#E84545">
      <animate attributeName="opacity" values="1;0.3;1" dur="1s" repeatCount="indefinite"/>
    </circle>
    <text x="392" y="210" font-family="serif" font-size="3" fill="#0F2E20" font-weight="700">Fed signals patient</text>
    <text x="392" y="214" font-family="serif" font-size="3" fill="#0F2E20" font-weight="700">approach on rate cuts</text>
    <line x1="392" y1="216" x2="488" y2="216" stroke="#0F2E20" stroke-width="0.2"/>
    <text x="392" y="220" font-family="serif" font-size="2.4" fill="#3A2818">WASHINGTON — Powell told</text>
    <text x="392" y="223.5" font-family="serif" font-size="2.4" fill="#3A2818">the Senate committee policy</text>
    <text x="392" y="227" font-family="serif" font-size="2.4" fill="#3A2818">remains data-dependent.</text>
    <line x1="392" y1="230" x2="488" y2="230" stroke="#888" stroke-width="0.2"/>
    <text x="392" y="234" font-family="sans-serif" font-size="2.3" fill="#0F2E20" font-weight="600">› RBI keeps repo at 6.50%</text>
    <text x="392" y="238" font-family="sans-serif" font-size="2.3" fill="#0F2E20" font-weight="600">› TCS beats Q3 estimates</text>
    <text x="392" y="242" font-family="sans-serif" font-size="2.3" fill="#0F2E20" font-weight="600">› Oil drops on demand worry</text>
    <text x="392" y="246" font-family="sans-serif" font-size="2.3" fill="#0F2E20" font-weight="600">› EU finalizes AI Act phase 2</text>
    <text x="392" y="250" font-family="sans-serif" font-size="2.3" fill="#0F2E20" font-weight="600">› Yen hits 3-month low</text>
    <text x="392" y="254" font-family="sans-serif" font-size="2.3" fill="#0F2E20" font-weight="600">› Adani group bonds rally</text>
    <text x="392" y="258" font-family="sans-serif" font-size="2.3" fill="#888">02:14 EST · updated now</text>
  </g>

  <g clip-path="url(#u5)">
    <rect x="500" y="200" width="100" height="60" fill="#050A07"/>
    <rect x="500" y="200" width="100" height="5" fill="#0F2E20"/>
    <circle cx="503" cy="202.5" r="0.8" fill="#E84545">
      <animate attributeName="opacity" values="1;0.2;1" dur="1s" repeatCount="indefinite"/>
    </circle>
    <text x="506" y="203.7" font-family="sans-serif" font-size="2.4" fill="#FAF6EC" font-weight="600">LIVE · Morning Call</text>
    <text x="582" y="203.7" font-family="monospace" font-size="2.4" fill="#D4A24C">08:42</text>
    <g>
      <rect x="502" y="208" width="46" height="22" fill="#0F2E20" stroke="#D4A24C" stroke-width="0.5"/>
      <circle cx="525" cy="217" r="4" fill="#F5C6A8"/>
      <ellipse cx="525" cy="216" rx="2.2" ry="2.5" fill="#2A1810"/>
      <path d="M 519 222 Q 525 219 531 222 L 531 230 L 519 230 Z" fill="#264035"/>
      <rect x="502" y="226" width="46" height="4" fill="#000" opacity="0.6"/>
      <text x="504" y="229" font-family="sans-serif" font-size="2.2" fill="#FAF6EC">Mudra · You</text>
      <circle cx="544" cy="228" r="0.8" fill="#97C459"/>
      <rect x="552" y="208" width="46" height="22" fill="#0F2E20"/>
      <circle cx="575" cy="217" r="4" fill="#E8C9A0"/>
      <ellipse cx="575" cy="216" rx="2.2" ry="2.5" fill="#3A2818"/>
      <path d="M 569 222 Q 575 219 581 222 L 581 230 L 569 230 Z" fill="#264035"/>
      <rect x="552" y="226" width="46" height="4" fill="#000" opacity="0.6"/>
      <text x="554" y="229" font-family="sans-serif" font-size="2.2" fill="#FAF6EC">A. Sharma · NY</text>
      <rect x="502" y="232" width="46" height="22" fill="#0F2E20"/>
      <circle cx="525" cy="241" r="4" fill="#D4A88A"/>
      <ellipse cx="525" cy="240" rx="2.2" ry="2.5" fill="#1A0A05"/>
      <path d="M 519 246 Q 525 243 531 246 L 531 254 L 519 254 Z" fill="#264035"/>
      <rect x="502" y="250" width="46" height="4" fill="#000" opacity="0.6"/>
      <text x="504" y="253" font-family="sans-serif" font-size="2.2" fill="#FAF6EC">R. Mehta · Mumbai</text>
      <rect x="552" y="232" width="46" height="22" fill="#0F2E20"/>
      <circle cx="575" cy="241" r="4" fill="#F0D2B0"/>
      <ellipse cx="575" cy="240" rx="2.2" ry="2.5" fill="#4A2A1A"/>
      <path d="M 569 246 Q 575 243 581 246 L 581 254 L 569 254 Z" fill="#264035"/>
      <rect x="552" y="250" width="46" height="4" fill="#000" opacity="0.6"/>
      <text x="554" y="253" font-family="sans-serif" font-size="2.2" fill="#FAF6EC">Client · London</text>
      <circle cx="594" cy="228" r="0.8" fill="#E84545"/>
      <circle cx="544" cy="252" r="0.8" fill="#97C459"/>
      <circle cx="594" cy="252" r="0.8" fill="#E84545"/>
    </g>
  </g>

  <g clip-path="url(#u6)">
    <rect x="225" y="270" width="230" height="80" fill="#0A1510"/>
    <rect x="225" y="270" width="230" height="6" fill="#0F2E20"/>
    <text x="228" y="274.5" font-family="sans-serif" font-size="3" fill="#D4A24C" font-weight="700">BEAVER · MARKET PULSE</text>
    <text x="320" y="274.5" font-family="sans-serif" font-size="2.4" fill="#FAF6EC">FII/DII · Sectors · Heatmap</text>
    <text x="430" y="274.5" font-family="monospace" font-size="2.4" fill="#97C459">● LIVE</text>
    <text x="228" y="282" font-family="sans-serif" font-size="2.4" fill="#FAF6EC" font-weight="600">FII / DII flows · last 15 days (₹ cr)</text>
    <line x1="228" y1="310" x2="318" y2="310" stroke="#264035" stroke-width="0.3"/>
    <g>
      <rect x="230" y="296" width="4" height="14" fill="#97C459"><animate attributeName="height" values="14;18;14" dur="3s" repeatCount="indefinite"/><animate attributeName="y" values="296;292;296" dur="3s" repeatCount="indefinite"/></rect>
      <rect x="236" y="310" width="4" height="8" fill="#E84545"/>
      <rect x="242" y="293" width="4" height="17" fill="#97C459"><animate attributeName="height" values="17;22;17" dur="2.5s" repeatCount="indefinite"/><animate attributeName="y" values="293;288;293" dur="2.5s" repeatCount="indefinite"/></rect>
      <rect x="248" y="310" width="4" height="11" fill="#E84545"/>
      <rect x="254" y="298" width="4" height="12" fill="#97C459"/>
      <rect x="260" y="310" width="4" height="6" fill="#E84545"/>
      <rect x="266" y="290" width="4" height="20" fill="#97C459"><animate attributeName="height" values="20;25;20" dur="2.8s" repeatCount="indefinite"/><animate attributeName="y" values="290;285;290" dur="2.8s" repeatCount="indefinite"/></rect>
      <rect x="272" y="310" width="4" height="14" fill="#E84545"/>
      <rect x="278" y="295" width="4" height="15" fill="#97C459"/>
      <rect x="284" y="310" width="4" height="9" fill="#E84545"/>
      <rect x="290" y="288" width="4" height="22" fill="#97C459"/>
      <rect x="296" y="310" width="4" height="12" fill="#E84545"/>
      <rect x="302" y="294" width="4" height="16" fill="#97C459"><animate attributeName="height" values="16;20;16" dur="2.2s" repeatCount="indefinite"/><animate attributeName="y" values="294;290;294" dur="2.2s" repeatCount="indefinite"/></rect>
      <rect x="308" y="310" width="4" height="7" fill="#E84545"/>
      <rect x="314" y="291" width="4" height="19" fill="#97C459"/>
    </g>
    <text x="228" y="328" font-family="sans-serif" font-size="2.2" fill="#97C459">FII +1,284 cr</text>
    <text x="270" y="328" font-family="sans-serif" font-size="2.2" fill="#E84545">DII -842 cr</text>
    <line x1="328" y1="280" x2="328" y2="345" stroke="#264035" stroke-width="0.3"/>
    <text x="332" y="282" font-family="sans-serif" font-size="2.4" fill="#FAF6EC" font-weight="600">NIFTY 50 · 5min</text>
    <text x="392" y="282" font-family="monospace" font-size="2.2" fill="#97C459">+0.42%</text>
    <g>
      <line x1="334" y1="295" x2="334" y2="305" stroke="#97C459" stroke-width="0.3"/>
      <rect x="332.5" y="298" width="3" height="5" fill="#97C459"/>
      <line x1="338" y1="293" x2="338" y2="307" stroke="#97C459" stroke-width="0.3"/>
      <rect x="336.5" y="296" width="3" height="6" fill="#97C459"/>
      <line x1="342" y1="296" x2="342" y2="304" stroke="#E84545" stroke-width="0.3"/>
      <rect x="340.5" y="298" width="3" height="4" fill="#E84545"/>
      <line x1="346" y1="290" x2="346" y2="302" stroke="#97C459" stroke-width="0.3"/>
      <rect x="344.5" y="293" width="3" height="6" fill="#97C459"/>
      <line x1="350" y1="288" x2="350" y2="298" stroke="#97C459" stroke-width="0.3"/>
      <rect x="348.5" y="290" width="3" height="6" fill="#97C459"/>
      <line x1="354" y1="290" x2="354" y2="296" stroke="#E84545" stroke-width="0.3"/>
      <rect x="352.5" y="291" width="3" height="3" fill="#E84545"/>
      <line x1="358" y1="285" x2="358" y2="294" stroke="#97C459" stroke-width="0.3"/>
      <rect x="356.5" y="287" width="3" height="5" fill="#97C459"/>
      <line x1="362" y1="282" x2="362" y2="290" stroke="#97C459" stroke-width="0.3"/>
      <rect x="360.5" y="284" width="3" height="4" fill="#97C459"/>
      <line x1="366" y1="284" x2="366" y2="291" stroke="#E84545" stroke-width="0.3"/>
      <rect x="364.5" y="285" width="3" height="3" fill="#E84545"/>
      <line x1="370" y1="280" x2="370" y2="289" stroke="#97C459" stroke-width="0.3"/>
      <rect x="368.5" y="282" width="3" height="5" fill="#97C459"/>
      <line x1="374" y1="278" x2="374" y2="285" stroke="#97C459" stroke-width="0.3"/>
      <rect x="372.5" y="280" width="3" height="3" fill="#97C459"/>
      <line x1="378" y1="280" x2="378" y2="288" stroke="#E84545" stroke-width="0.3"/>
      <rect x="376.5" y="281" width="3" height="4" fill="#E84545"/>
      <line x1="382" y1="276" x2="382" y2="284" stroke="#97C459" stroke-width="0.3"/>
      <rect x="380.5" y="278" width="3" height="4" fill="#97C459"/>
      <line x1="386" y1="274" x2="386" y2="280" stroke="#97C459" stroke-width="0.3"/>
      <rect x="384.5" y="275" width="3" height="3" fill="#97C459"/>
    </g>
    <text x="332" y="320" font-family="sans-serif" font-size="2.2" fill="#FAF6EC">24,856.40</text>
    <text x="358" y="320" font-family="sans-serif" font-size="2.2" fill="#97C459">+103.2 pts</text>
    <text x="332" y="328" font-family="sans-serif" font-size="2.2" fill="#888">Vol 142M  ·  Range 24,742-24,891</text>
    <text x="332" y="334" font-family="sans-serif" font-size="2.2" fill="#888">VWAP 24,818  ·  RSI 58</text>
    <text x="332" y="340" font-family="sans-serif" font-size="2.2" fill="#D4A24C">Signal: Bullish · trend intact</text>
    <line x1="396" y1="280" x2="396" y2="345" stroke="#264035" stroke-width="0.3"/>
    <text x="400" y="282" font-family="sans-serif" font-size="2.4" fill="#FAF6EC" font-weight="600">Sector heatmap</text>
    <g font-family="sans-serif" font-size="2">
      <rect x="400" y="285" width="14" height="8" fill="#3B6D11"/><text x="402" y="290" fill="#FAF6EC">IT +2.1</text>
      <rect x="416" y="285" width="14" height="8" fill="#639922"/><text x="418" y="290" fill="#FAF6EC">FIN +0.8</text>
      <rect x="432" y="285" width="14" height="8" fill="#97C459"/><text x="434" y="290" fill="#0F2E20">PHAR+0.4</text>
      <rect x="400" y="295" width="14" height="8" fill="#A32D2D"/><text x="402" y="300" fill="#FAF6EC">OIL -1.2</text>
      <rect x="416" y="295" width="14" height="8" fill="#E84545"/><text x="418" y="300" fill="#FAF6EC">PSU -0.6</text>
      <rect x="432" y="295" width="14" height="8" fill="#97C459"/><text x="434" y="300" fill="#0F2E20">FMCG+0.3</text>
      <rect x="400" y="305" width="14" height="8" fill="#639922"/><text x="402" y="310" fill="#FAF6EC">AUTO+0.7</text>
      <rect x="416" y="305" width="14" height="8" fill="#3B6D11"/><text x="418" y="310" fill="#FAF6EC">META+1.8</text>
      <rect x="432" y="305" width="14" height="8" fill="#E84545"/><text x="434" y="310" fill="#FAF6EC">RLT -0.9</text>
      <rect x="400" y="315" width="14" height="8" fill="#97C459"/><text x="402" y="320" fill="#0F2E20">CONS+0.2</text>
      <rect x="416" y="315" width="14" height="8" fill="#639922"/><text x="418" y="320" fill="#FAF6EC">INFR+0.6</text>
      <rect x="432" y="315" width="14" height="8" fill="#3B6D11"/><text x="434" y="320" fill="#FAF6EC">DEFE+1.4</text>
    </g>
    <text x="400" y="330" font-family="sans-serif" font-size="2.2" fill="#888">Top mover: META · +1.8%</text>
    <text x="400" y="335" font-family="sans-serif" font-size="2.2" fill="#888">Worst: OIL · -1.2%</text>
    <text x="400" y="340" font-family="sans-serif" font-size="2.2" fill="#D4A24C">Breadth: 32 ▲ · 18 ▼</text>
  </g>

  <g opacity="0.4">
    <rect x="50" y="190" width="120" height="80" fill="url(#screenGlow8)"/>
    <rect x="160" y="190" width="120" height="80" fill="url(#screenGlow8)"/>
    <rect x="270" y="190" width="120" height="80" fill="url(#screenGlow8)"/>
    <rect x="380" y="190" width="120" height="80" fill="url(#screenGlow8)"/>
    <rect x="490" y="190" width="120" height="80" fill="url(#screenGlow8)"/>
    <rect x="215" y="260" width="250" height="100" fill="url(#screenGlow8)"/>
  </g>

  <g id="analyst8">
    <path d="M 295 360 L 295 395 Q 295 410 305 410 L 375 410 Q 385 410 385 395 L 385 360 Q 385 340 370 335 L 310 335 Q 295 340 295 360 Z" fill="#0F2118"/>
    <line x1="340" y1="340" x2="340" y2="408" stroke="#264035" stroke-width="0.4"/>
    <ellipse cx="340" cy="332" rx="22" ry="6" fill="#0F2118"/>
    <rect x="288" y="378" width="10" height="22" rx="2" fill="#1A1108"/>
    <rect x="382" y="378" width="10" height="22" rx="2" fill="#1A1108"/>
    <path d="M 308 360 Q 312 332 340 328 Q 368 332 372 360 L 378 425 L 302 425 Z" fill="#0F2E20"/>
    <path d="M 332 330 Q 340 326 348 330 L 348 336 L 332 336 Z" fill="#FAF6EC"/>
    <path d="M 308 360 Q 312 332 340 328 L 340 345 Q 320 348 312 365 Z" fill="#0A1A14" opacity="0.6"/>
    <rect x="334" y="318" width="12" height="14" rx="2" fill="#C9A084"/>
    <ellipse cx="340" cy="305" rx="15" ry="17" fill="#1A0A05"/>
    <path d="M 326 300 Q 332 290 340 290 Q 348 290 354 300" stroke="#0A0502" stroke-width="0.6" fill="none" opacity="0.5"/>
    <ellipse cx="340" cy="320" rx="6" ry="4" fill="#1A0A05"/>
    <ellipse cx="325" cy="306" rx="1.5" ry="2.8" fill="#C9A084"/>
    <ellipse cx="355" cy="306" rx="1.5" ry="2.8" fill="#C9A084"/>
    <path d="M 326 296 Q 340 282 354 296" fill="none" stroke="#0A0A0A" stroke-width="2.5"/>
    <ellipse cx="324" cy="306" rx="3.5" ry="5" fill="#0A0A0A"/>
    <ellipse cx="356" cy="306" rx="3.5" ry="5" fill="#0A0A0A"/>
    <circle cx="324" cy="306" r="1.5" fill="#D4A24C"/>
    <circle cx="356" cy="306" r="1.5" fill="#D4A24C"/>
    <path d="M 370 365 Q 395 372 410 380 L 415 392 Q 398 392 378 386 Z" fill="#0F2E20"/>
    <ellipse cx="418" cy="390" rx="6" ry="4" fill="#C9A084"/>
    <animateTransform attributeName="transform" type="translate" values="0 0; 0.5 0; 0 0; -0.5 0; 0 0" dur="7s" repeatCount="indefinite"/>
  </g>

  <rect x="280" y="385" width="120" height="10" rx="2" fill="#0F2118"/>
  <g fill="#264035">
    <rect x="284" y="388" width="3" height="2"/><rect x="289" y="388" width="3" height="2"/>
    <rect x="294" y="388" width="3" height="2"/><rect x="299" y="388" width="3" height="2"/>
    <rect x="304" y="388" width="3" height="2"/><rect x="309" y="388" width="3" height="2"/>
    <rect x="314" y="388" width="3" height="2"/><rect x="319" y="388" width="3" height="2"/>
    <rect x="324" y="388" width="3" height="2"/><rect x="329" y="388" width="3" height="2"/>
    <rect x="334" y="388" width="3" height="2"/><rect x="339" y="388" width="3" height="2"/>
    <rect x="344" y="388" width="3" height="2"/><rect x="349" y="388" width="3" height="2"/>
    <rect x="354" y="388" width="3" height="2"/><rect x="359" y="388" width="3" height="2"/>
    <rect x="364" y="388" width="3" height="2"/><rect x="369" y="388" width="3" height="2"/>
    <rect x="374" y="388" width="3" height="2"/><rect x="379" y="388" width="3" height="2"/>
    <rect x="384" y="388" width="3" height="2"/><rect x="389" y="388" width="3" height="2"/>
    <rect x="394" y="388" width="3" height="2"/>
  </g>

  <g>
    <rect x="465" y="370" width="14" height="16" rx="1.5" fill="#FAF6EC" stroke="#0F2E20" stroke-width="0.6"/>
    <ellipse cx="472" cy="370" rx="7" ry="2" fill="#3A2818"/>
    <path d="M 479 374 Q 486 375 486 380 Q 486 384 479 384" fill="none" stroke="#0F2E20" stroke-width="1.2"/>
    <text x="467.5" y="383" font-family="serif" font-size="3.2" fill="#0F2E20" font-weight="700">B</text>
    <path d="M 468 367 Q 466 363 468 360 Q 470 357 468 354" fill="none" stroke="#D4A24C" stroke-width="0.5" opacity="0.5">
      <animate attributeName="opacity" values="0.5;0.1;0.5" dur="2s" repeatCount="indefinite"/>
    </path>
    <path d="M 472 367 Q 474 363 472 360 Q 470 357 472 354" fill="none" stroke="#D4A24C" stroke-width="0.5" opacity="0.4">
      <animate attributeName="opacity" values="0.4;0.05;0.4" dur="2.4s" repeatCount="indefinite"/>
    </path>
  </g>

  <rect x="120" y="370" width="50" height="14" rx="1" fill="#0F2E20"/>
  <rect x="120" y="370" width="3" height="14" fill="#D4A24C"/>
  <line x1="128" y1="375" x2="165" y2="375" stroke="#FAF6EC" stroke-width="0.3" opacity="0.4"/>
  <line x1="128" y1="378" x2="165" y2="378" stroke="#FAF6EC" stroke-width="0.3" opacity="0.4"/>
  <line x1="128" y1="381" x2="155" y2="381" stroke="#FAF6EC" stroke-width="0.3" opacity="0.4"/>
  <rect x="135" y="384" width="35" height="1.5" rx="0.5" fill="#D4A24C"/>

  <rect x="195" y="372" width="14" height="22" rx="2" fill="#0A0A0A"/>
  <rect x="196" y="374" width="12" height="18" rx="0.5" fill="#0F2E20"/>
  <circle cx="202" cy="392" r="0.6" fill="#264035"/>

  <rect id="bi8-focus" x="56" y="194" width="108" height="72" fill="none" stroke="#D4A24C" stroke-width="1.4" rx="3" opacity="0.85"/>

  <g transform="translate(36, 38)">
    <rect x="0" y="0" width="76" height="14" rx="2" fill="#0F2E20" fill-opacity="0.85" stroke="#D4A24C" stroke-width="0.4"/>
    <text x="6" y="9.5" font-family="sans-serif" font-size="6" fill="#D4A24C" font-weight="700" letter-spacing="0.5">BEAVER · NYC</text>
  </g>
  <g transform="translate(552, 38)">
    <rect x="0" y="0" width="92" height="14" rx="2" fill="#0F2E20" fill-opacity="0.85" stroke="#D4A24C" stroke-width="0.4"/>
    <text x="6" y="9.5" font-family="monospace" font-size="6" fill="#FAF6EC" id="bi8-clock">08:42:18 EST</text>
  </g>

  <g id="bi8-timeline">
    <rect x="40" y="430" width="600" height="50" rx="6" fill="#0A1510" stroke="#0F2E20" stroke-width="0.8"/>
    <text id="bi8-overall" x="630" y="442" text-anchor="end" font-family="monospace" font-size="6" fill="#FAF6EC">0 / 5 complete</text>
    <line x1="56" y1="463" x2="624" y2="463" stroke="#264035" stroke-width="0.6"/>
    <line id="bi8-fill" x1="56" y1="463" x2="56" y2="463" stroke="url(#amberAccent8)" stroke-width="2" stroke-linecap="round"/>

    <g id="bi8-nodes" font-family="sans-serif" font-size="5.6">
      <g data-i="0" transform="translate(56, 463)">
        <circle r="3.6" fill="#0A1510" stroke="#264035" stroke-width="0.8" class="dot"/>
        <text y="-7" text-anchor="start" fill="#888" class="label" font-weight="600">1 · Data fetching</text>
      </g>
      <g data-i="1" transform="translate(198, 463)">
        <circle r="3.6" fill="#0A1510" stroke="#264035" stroke-width="0.8" class="dot"/>
        <text y="-7" text-anchor="middle" fill="#888" class="label" font-weight="600">2 · Data analysis</text>
      </g>
      <g data-i="2" transform="translate(340, 463)">
        <circle r="3.6" fill="#0A1510" stroke="#264035" stroke-width="0.8" class="dot"/>
        <text y="-7" text-anchor="middle" fill="#888" class="label" font-weight="600">3 · Human intelligence</text>
      </g>
      <g data-i="3" transform="translate(482, 463)">
        <circle r="3.6" fill="#0A1510" stroke="#264035" stroke-width="0.8" class="dot"/>
        <text y="-7" text-anchor="middle" fill="#888" class="label" font-weight="600">4 · War room</text>
      </g>
      <g data-i="4" transform="translate(624, 463)">
        <circle r="3.6" fill="#0A1510" stroke="#264035" stroke-width="0.8" class="dot"/>
        <text y="-7" text-anchor="end" fill="#888" class="label" font-weight="600">5 · Final report</text>
      </g>
    </g>
  </g>
</svg>
`;

const screenSeq = [
  { x: 56,  y: 194, w: 108, h: 72, t: 0,    cap: 'Data fetching · Bloomberg feeds'        },
  { x: 215, y: 264, w: 250, h: 92, t: 1.5,  cap: 'Data fetching · live FII/DII flows'    },
  { x: 276, y: 194, w: 108, h: 72, t: 3,    cap: 'Data analysis · backtest engine'       },
  { x: 386, y: 194, w: 108, h: 72, t: 6,    cap: 'Human intelligence · macro wire'       },
  { x: 166, y: 194, w: 108, h: 72, t: 7.5,  cap: 'Human intelligence · Claude synthesis' },
  { x: 496, y: 194, w: 108, h: 72, t: 9,    cap: 'War room · client briefing'            },
  { x: 215, y: 264, w: 250, h: 92, t: 12,   cap: 'Final report · Beaver Pulse delivered' },
];

const stages = [
  { t: 0,  end: 3,  },
  { t: 3,  end: 6,  },
  { t: 6,  end: 9,  },
  { t: 9,  end: 12, },
  { t: 12, end: 15, },
];

const NODE_X_START = 56;
const NODE_X_END   = 624;

export default function CommandCenterLoader({ ticker }) {
  const containerRef = useRef(null);
  const timerRef     = useRef(null);
  const captionRef   = useRef(null);

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;
    const t = requestAnimationFrame(() => { root.style.opacity = '1'; });
    return () => cancelAnimationFrame(t);
  }, []);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  useEffect(() => {
    const C = containerRef.current;
    if (!C) return;

    const focus   = C.querySelector('#bi8-focus');
    const clock   = C.querySelector('#bi8-clock');
    const fill    = C.querySelector('#bi8-fill');
    const overall = C.querySelector('#bi8-overall');
    const nodes   = C.querySelectorAll('#bi8-nodes > g');

    if (!focus || !fill || !overall || !nodes.length) return;

    let start = performance.now();
    let raf;

    function frame(now) {
      let elapsed = (now - start) / 1000;

      if (elapsed >= 15) {
        start = now;
        elapsed = 0;
      }

      const timer = timerRef.current;
      const cap   = captionRef.current;

      const s = Math.floor(elapsed % 60).toString().padStart(2, '0');
      if (timer) timer.textContent = `00:${s} / 00:15`;

      const baseSec = 8 * 3600 + 42 * 60 + 18;
      const total   = baseSec + Math.floor(elapsed);
      const hh = Math.floor(total / 3600).toString().padStart(2, '0');
      const mm = Math.floor((total % 3600) / 60).toString().padStart(2, '0');
      const ss = Math.floor(total % 60).toString().padStart(2, '0');
      if (clock) clock.textContent = `${hh}:${mm}:${ss} EST`;

      let active = screenSeq[0];
      for (const sc of screenSeq) if (elapsed >= sc.t) active = sc;

      const cx = parseFloat(focus.getAttribute('x'));
      const cy = parseFloat(focus.getAttribute('y'));
      const cw = parseFloat(focus.getAttribute('width'));
      const ch = parseFloat(focus.getAttribute('height'));
      const ease = 0.18;
      focus.setAttribute('x',      cx + (active.x - cx) * ease);
      focus.setAttribute('y',      cy + (active.y - cy) * ease);
      focus.setAttribute('width',  cw + (active.w - cw) * ease);
      focus.setAttribute('height', ch + (active.h - ch) * ease);
      focus.setAttribute('opacity', 0.65 + 0.3 * Math.sin(elapsed * 4));

      if (cap) cap.textContent = active.cap;

      const progress = Math.min(1, elapsed / 15);
      const fillX    = NODE_X_START + (NODE_X_END - NODE_X_START) * progress;
      fill.setAttribute('x2', fillX);

      let completed = 0;
      nodes.forEach((g, i) => {
        const dot   = g.querySelector('.dot');
        const label = g.querySelector('.label');
        const st    = stages[i];
        if (!dot || !label || !st) return;

        if (elapsed >= st.end) {
          dot.setAttribute('fill',         '#D4A24C');
          dot.setAttribute('stroke',       '#F4C26B');
          dot.setAttribute('stroke-width', '0.8');
          dot.setAttribute('r',            '4.2');
          label.setAttribute('fill',       '#FAF6EC');
          completed++;
        } else if (elapsed >= st.t) {
          const pulse = 4.2 + 0.7 * Math.sin(elapsed * 8);
          dot.setAttribute('fill',         '#0A1510');
          dot.setAttribute('stroke',       '#D4A24C');
          dot.setAttribute('stroke-width', '1.4');
          dot.setAttribute('r',            pulse);
          label.setAttribute('fill',       '#D4A24C');
        } else {
          dot.setAttribute('fill',         '#0A1510');
          dot.setAttribute('stroke',       '#264035');
          dot.setAttribute('stroke-width', '0.8');
          dot.setAttribute('r',            '3.6');
          label.setAttribute('fill',       '#5F7A6C');
        }
      });

      overall.textContent = `${completed} / 5 complete`;
      overall.setAttribute('fill', completed === 5 ? '#97C459' : '#FAF6EC');

      raf = requestAnimationFrame(frame);
    }

    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      zIndex: 9999,
      background: '#050A07',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div
        ref={containerRef}
        style={{
          width: '100%',
          maxWidth: 1200,
          padding: '0 32px',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          opacity: 0,
          transition: 'opacity 200ms ease-in',
        }}
      >
        {ticker && (
          <div style={{ textAlign: 'center', padding: '0 4px 10px', letterSpacing: '2.5px', fontSize: 11, color: '#997733', fontFamily: 'monospace' }}>
            ANALYZING {ticker}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 4px', fontSize: 12 }}>
          <span style={{ fontWeight: 600, color: '#D4A24C', letterSpacing: '1.2px' }}>
            BEAVER INTELLIGENCE · COMMAND CENTER
          </span>
          <span ref={timerRef} style={{ color: '#888', fontFamily: 'monospace' }}>00:00 / 00:15</span>
        </div>

        {/* SVG rendered via dangerouslySetInnerHTML to avoid JSX conversion of complex SVG */}
        <div style={{ perspective: '1500px', perspectiveOrigin: 'center center' }}>
          <div
            dangerouslySetInnerHTML={{ __html: SVG_MARKUP }}
            style={{
              transform: 'rotateX(8deg) translateZ(-30px)',
              transition: 'transform 600ms ease-out',
            }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 4px 4px', fontSize: 12 }}>
          <span ref={captionRef} style={{ color: '#D4A24C', fontWeight: 500 }}>
            Data fetching · pulling live feeds
          </span>
          <span style={{ color: '#666', fontFamily: 'monospace', fontSize: 11 }}>
            NYC · Boston · Ahmedabad
          </span>
        </div>

        {/* Buttons hidden — kept for JS hook parity with source */}
        <div style={{ display: 'none' }}>
          <button id="bi8-replay">Replay</button>
          <button id="bi8-pause">Pause</button>
        </div>
      </div>
    </div>
  );
}
