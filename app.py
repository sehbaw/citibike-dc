import os, colorcet, param as pm, holoviews as hv, panel as pn, datashader as ds
import intake
import xyzservices.providers as xyz
from holoviews.element import tiles as hvts
from holoviews.operation.datashader import rasterize, shade, spread
from collections import OrderedDict as odict


pn.extension(template="fast")

df = pd.read_csv("https://raw.githubusercontent.com/sehbaw/datasets/refs/heads/main/external-data/cleaned_tripdata.csv")

dataset = os.getenv("DS_DATASET", "https://raw.githubusercontent.com/sehbaw/datasets/refs/heads/main/external-data/cleaned_tripdata.csv")
catalog = intake.open_catalog('catalog.yml')
source  = getattr(catalog, dataset)

plots  = odict([(source.metadata['plots'][p].get('label',p),p) for p in source.plots])
fields = odict([(v.get('label',k),k) for k,v in source.metadata['fields'].items()])
aggfns = odict([(f.capitalize(),getattr(ds,f)) for f in ['count','sum','min','max','mean','var','std']])

norms  = odict(Histogram_Equalization='eq_hist', Linear='linear', Log='log', Cube_root='cbrt')
cmaps  = odict([(n,colorcet.palette[n]) for n in ['fire', 'bgy', 'bgyw', 'bmy', 'gray', 'kbc']])

maps   = ['EsriImagery', 'EsriUSATopo', 'EsriTerrain', 'EsriStreet', 'OSM']
bases  = odict([(name, getattr(hvts, name)().relabel(name)) for name in maps])
gopts  = hv.opts.Tiles(responsive=True, xaxis=None, yaxis=None, bgcolor='black', show_grid=False)

class Explorer(pm.Parameterized):
    plot          = pm.Selector(plots)
    field         = pm.Selector(fields)
    agg_fn        = pm.Selector(aggfns)
    
    normalization = pm.Selector(norms)
    cmap          = pm.Selector(cmaps)
    spreading     = pm.Integer(0, bounds=(0, 5))
    
    basemap       = pm.Selector(bases)
    data_opacity  = pm.Magnitude(1.00)
    map_opacity   = pm.Magnitude(0.75)
    show_labels   = pm.Boolean(True)

    @pm.depends('plot')
    def elem(self):
        return getattr(source.plot, self.plot)()

    @pm.depends('field', 'agg_fn')
    def aggregator(self):
        field = None if self.field == "counts" else self.field
        return self.agg_fn(field)

    @pm.depends('map_opacity', 'basemap')
    def tiles(self):
        return self.basemap.opts(gopts).opts(alpha=self.map_opacity)

    @pm.depends('show_labels')
    def labels(self):
        return hv.Tiles(xyz.CartoDB.PositronOnlyLabels()).opts(level='annotation', alpha=1 if self.show_labels else 0)


    def viewable(self,**kwargs):
        rasterized = rasterize(hv.DynamicMap(self.elem), aggregator=self.aggregator, width=800, height=400)
        shaded     = shade(rasterized, cmap=self.param.cmap, normalization=self.param.normalization)
        spreaded   = spread(shaded, px=self.param.spreading, how="add")
        dataplot   = spreaded.apply.opts(alpha=self.param.data_opacity, show_legend=False)
        
        return hv.DynamicMap(self.tiles) * dataplot * hv.DynamicMap(self.labels)
    
explorer = Explorer(name="")


#pn.Row(widget, pn.bind(hello_world, widget)).servable()

panel = pn.Row(pn.column(pn.Param(explorer.param, expand_button=False)), explorer.viewable)
panel.servable("CIti Bike DC Dashboards")


#######map 

class Explorer2(pm.Parameterized):
    plot = pm.Selector(plots)
    field = pm.Selector(fields)
    agg_fn = pm.Selector(aggfns)

    normalizaton = pm.Selector(norms)
    cmap = pm.Selector(cmaps)
    spreading = pm.Integer(0, bounds=(0,5))

    basemap = pm.Selector(bases)
    data_opacity = pm.Magnitude(1.00)
    map_opacity = pm.Magnitude(0.75)
    pm.Boolean(True)

    def view(self, **kwargs):
        field = None if self.field == "counts" else self.field
        rasterized = rasterize(hv.DynamicMap(getattr(source.plot, self.plot)),
                aggregator=self.agg_fn(field), width=900, height=500)
        shaded = shade(rasterized, cmap=self.cmap, normalization=self.normalization)
        spreaded = spread(shaded, px=self.spreading, how="add")
        dataplot = spreaded.opts(alpha=self.data_opacity, show_legend=False)

        tiles      = self.basemap.opts(gopts).opts(alpha=self.map_opacity)
        labels     = hv.Tiles(xyz.CartoDB.PositronOnlyLabels()).opts(level='annotation', alpha=1 if self.show_labels else 0)
        return tiles * dataplot * labels


explorer2 = Explorer2(name="")



panel = pn.Row(pn.Column(logo, pn.Param(explorer.param, expand_button=False)), explorer.viewable())
panel.servable("CitiBikes in DC Dashboard")
