import kotlin.random.Random

open class card(id : Int,
            name : String,
            img : String,
            description : String,
            type : Int,
            rarity : Int,
            gen : Int
            spe : Int
            set : Int
            ) {

    val id : Int,
    val name : String,
    val img : String,
    val description : String,
    val type : Int,
    val rarity : Int,
    val quality : Int,
    val gen : Int
    val spe : Int
    val set : Int

    init {
        this.id = id
        this.name = name
        this.img = img
        this.description = description
        this.type = type
        this.rarity = rarity
        this.quality = this.quality
        this.gen = gen
        this.spe = spe
        this.set = set
    }

    fun AddQuality() {

    }
    fun Draw() {

    }
}