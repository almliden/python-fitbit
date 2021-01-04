# MongoDB Queries:

## Distinct date

db.heart.distinct( "activities-heart-intraday.dataset.value" ).sort()

## Get min for date

db.heart.aggregate(
  [
    { 
      $match: { "activities-heart.dateTime": "2021-01-02" }
    }, 
    { 
      $group: { _id: "$time", min: { $min: "$activities-heart-intraday.dataset.value" } }
    } 
  ]
)

## Get sorted

db.heart.aggregate([
  { 
    $match: { "activities-heart.dateTime": "2021-01-02" }
  }, 
  { 
    $sort: { "activities-heart-intraday.dataset.value" : 1 }
  },
  { 
    $limit: 1 
  }
])


$limit does not to anything for us here since we already have the document

## Get Resting Heart Rate: 

db.heart.aggregate([
  { 
    $match: { "activities-heart.dateTime": "2021-01-02" }
  }, 
  { 
    $sort: { "activities-heart-intraday.dataset.value" : 1 }
  },
  { 
    $limit: 1 
  },

  {
    $project: { 
      day: "$activities-heart.dateTime",
      avg: "$averageHeartRate",
      resting: "$activities-heart.value.restingHeartRate"
     }
  }
])

## Heart Rate series

db.heart.aggregate([
  { 
    $sort: { "activities-heart.dateTime" : 1 }
  },
  {
    $project: { 
      day: "$activities-heart.dateTime",
      resting: "$activities-heart.value.restingHeartRate"
     }
  }
])

# Average/Max/Min HeartRate By Day

db.heart.aggregate([
  {$unwind: "$activities-heart-intraday.dataset"},
  {
    $group: {
      _id : "$_id",
      averageHeartRate: { $avg: "$activities-heart-intraday.dataset.value" },
      max: { $max: "$activities-heart-intraday.dataset.value" },
      min: { $min: "$activities-heart-intraday.dataset.value" },
      date: { $first: "$activities-heart.dateTime" }
    }
  },
  {
    $sort: { date: 1 }
  }
])

