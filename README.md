# Montana DOT RWIS for Home Assistant

![License](https://img.shields.io/badge/license-CC0%201.0-blue.svg)

Road weather readings and camera stills from Montana Department of Transportation (MDT) Road Weather Information System (RWIS) sites.

Requires Home Assistant 2026.10 or newer.

## Get an API key

Email mdtrwis@mt.gov and ask for an ATMS conditions API key. One key covers every site, so you only need one no matter how many sites you add. API reference: https://app.mdt.mt.gov/atms/swagger-ui/index.html

## Install

With HACS:

1. HACS > three-dot menu > Custom repositories.
2. Add `https://github.com/nickpdawson/MDT_RWIS`, type Integration.
3. Install "Montana DOT RWIS" and restart Home Assistant.

By hand: copy `custom_components/mdt_rwis` into your config's `custom_components/` folder and restart.

## Set up

Settings > Devices & services > Add integration > Montana DOT RWIS. Enter the key, then pick a site. Add the integration again for each extra site; the key form is prefilled.

## Entities

Each site is one device with these entities:

| Entity | Unit |
| --- | --- |
| Air temperature | °F |
| Dew point | °F |
| Humidity | % |
| Wind speed | mph |
| Wind gust | mph |
| Wind direction | ° (or a compass label if the site reports text) |
| Precipitation rate | in/h |
| Accumulated precipitation | in |
| Precipitation type | text, for example "No Precipitation" |
| Precipitation intensity | text |
| Observation time | timestamp (diagnostic) |
| Surface temperature | °F |
| Surface condition | text |
| One camera per site camera | JPEG still |

Wind gust, accumulated precipitation, precipitation type and intensity, observation time and the two surface sensors only appear if the site reports them. Home Assistant converts units to your system settings.

Observation time is when the station took the reading, not when Home Assistant polled. If it stops moving, the station has stopped reporting.

Field names were checked against a live payload from site 564001 (Karst, US-191) on 2026-10-26. Karst has no pavement sensors, so the surface field names (`surfaceTemperature`, `surfaceCondition`) are still unverified. If your site has a surface block and those sensors don't appear, attach diagnostics to an issue.

## Options

Configure > Update interval: 5 to 60 minutes, default 15. MDT collects new data every 15 minutes from the top of the hour, so polling faster only repeats the same values.

## Troubleshooting

- "Invalid API key" or a reauth prompt: MDT rejected the key. Enter a new one in the reauth form; it is applied to every site that used the old key.
- Camera stills only refetch when MDT posts a new image.
- Settings > Devices & services > Montana DOT RWIS > three-dot menu > Download diagnostics gives a payload dump with the key removed. Attach it to issues.

Debug logging:

```yaml
logger:
  logs:
    custom_components.mdt_rwis: debug
```

Report problems at https://github.com/nickpdawson/MDT_RWIS/issues.

## Breaking changes in 2.0.0

- Files moved to `custom_components/mdt_rwis/`. Manual installs must delete the old files in `custom_components/` and copy the new folder.
- Home Assistant 2026.10 is the minimum.
- Sensors and cameras for a site now share one device. The old second device is removed when it is empty.
- Entity names come from Home Assistant translations, so friendly names change (for example "RWIS Bozeman Pass Temperature" becomes "RWIS Bozeman Pass Air temperature"). Existing entity IDs and history are kept.
- The update interval moved to the integration's options. Values under 5 minutes are raised to 5.
- The `mdt_rwis.clear_camera_cache` service is gone. It was never registered.

## License

CC0 1.0 Universal. See [LICENSE](LICENSE).
