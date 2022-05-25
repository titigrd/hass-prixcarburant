# Intégration Prix Carburant pour Home-Assistant

Récupération du prix des carburant selon les données de https://www.prix-carburants.gouv.fr/
Via une distance maximum du domicile (localisation renseignée dans Home-Assistant) ou via une liste d'ID.

## Installation

### HACS

Non disponibe actuellement

### Manuelle

Copier le dossier `prix_carburant` dans le dossier `config/custom_components` de votre Home-Assistant.

## Configuration

### via l'interface

Ajoutez une nouvelle intégration, recherchez `Prix Carburant` et remplissez les champs demandés.

### via configuration.yml

#### A partir de la localisation Home-Assistant

Indiquez une distance maximale via `max_km`, par exemple:

```yaml
sensor:
  platform: prix_carburant
  max_km: 10
```

#### A partir d'une liste d'ID

Récupérer l'ID des stations voulues sur https://www.prix-carburants.gouv.fr/. Pour cela chercher la station, cliquer sur le logo station sur la carte, passer le curseur sur `Voir plan` et noter le numéro qui apparait en bas de votre navigateur. Exemple avec Firefox :

![Récupération d'ID avec Firefox](readme_firefoxid.png)

Puis dans le fichier configuration.yaml, mettre par exemple :

```yaml
sensor:
  platform: prix_carburant
  stations:
    - 59000009
    - 59000080
```

## Dashboard

Exemple de configuration avec [multiple-entity-row](https://github.com/benct/lovelace-multiple-entity-row):

![multiple-entity-row](readme_multipleentityrow.png)

```yaml
type: entities
entities:
  - entity: sensor.station_mastation_sp98
    type: custom:multiple-entity-row
    name: Ma Station
    show_state: false
    entities:
      - entity: sensor.station_mastation_e10
        name: E10
      - entity: sensor.station_mastation_sp98
        name: SP98
```

## Crédits

Fork de https://github.com/max5962/prixCarburant-home-assistant
